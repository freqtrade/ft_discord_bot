import argparse
import discord
import logging
import rapidjson

from datetime import datetime, timedelta
from pathlib import Path
from tabulate import tabulate
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ft_discord_command_bot")

allowed_managers = [
    "Hippocritical#5103",
    "froggleston#5424",
    "xmatthias#2871",
    "stash86#2488",
    "Perkmeister#2394",
    "@JoeSchr#5578"
]


class ft_discord_command_bot(discord.Client):

    def setup(self, commandfile):
        self._commandfile = commandfile
        self.base_commands = {}
        self.rate_limited_calls = {}

    def _version(self) -> str:
        return "1.00"

    def _on_ready(self):
        print(f'We have logged in as {self.user}')

    def _uri_validator(self, x):
        result = urlparse(x)
        return all([result.scheme, result.netloc])

    def load_commands(self):
        if self._uri_validator(self._commandfile):
            try:
                resp = requests.get(self._commandfile).text
                self.base_commands = rapidjson.loads(
                    resp,
                    parse_mode=rapidjson.PM_COMMENTS |
                    rapidjson.PM_TRAILING_COMMAS)
            except ConnectionError as e:
                logger.warning("Connection error", e)
                raise Exception("Cannot connect to remote commands list")
            except rapidjson.JSONDecodeError as e:
                logger.warning("Cannot decode JSON", e)
                raise Exception("Cannot parse remote JSON file", e)
        else:
            file = Path(self._commandfile)
            if file.is_file():
                with file.open("r") as f:
                    self.base_commands = rapidjson.load(
                        f,
                        parse_mode=rapidjson.PM_COMMENTS |
                        rapidjson.PM_TRAILING_COMMAS)
            else:
                logger.warning(f"Could not load commands file {file}.")
                raise Exception("Cannot load local commands list")

    def print_commands(self):
        return tabulate(
            {"COMMANDS": sorted(self.base_commands.keys())},
            headers='keys',
            tablefmt="plain")

    def process_command(self, message):
        cmd = message.lstrip("*")
        if cmd in self.base_commands:
            return self.base_commands[cmd]

    def _rate_limited(self, call=None, limit_sec=20):
        if call is not None:
            if self.rate_limited_calls[call] is not None:
                elapsed = datetime.now() - self.rate_limited_calls[call]
                if elapsed <= timedelta(seconds=limit_sec):
                    return True

            self.rate_limited_calls[call] = datetime.now()

        return False

    async def on_message(self, message):
        # don't let the bot reply to itself
        if message.author == self.user:
            return

        cmdstring = message.content

        # if discord reply used
        reply = None
        if message.type == discord.MessageType.reply:
            reference = await message.channel.fetch_message(
                message.reference.message_id)
            reply = reference.author

        # if mentioning a user specifically with `**cmd @user`
        mention = None
        cmds = cmdstring.split(" ")
        cmd = cmds[0]
        if len(cmds) > 1:
            mention = cmds[1]

        # all commands start with **. this can be customised.
        if cmd.startswith('**'):
            if cmd == "**help":
                # send help
                await message.channel.send(f"```{self.print_commands()}```")

            elif cmd == "**reload_commands":
                # reload command list from supplied file or URL
                # if you are in the allowed user list
                if str(message.author) in allowed_managers:
                    try:
                        self.load_commands()
                        await message.channel.send(
                            "Reloaded commands")
                    except Exception as e:
                        await message.channel.send(
                            "Unable to reload commands: ", e)

            elif cmd == "**test_ratelimit":
                # rate limiting calls example
                if self._rate_limited(call=cmd):
                    await message.channel.send(
                        f"The Oracle just provided some information \
                        about {cmd} and needs time to recover.")
                    return

            else:
                # check command against known loaded list of commands
                resp = self.process_command(cmd)

                if resp:
                    if reply:
                        # if replying to someone using discords reply feature
                        await message.channel.send(f"{reply.mention} {resp}")
                    elif mention:
                        # if mentioning a user specifically with `**cmd @user`
                        await message.channel.send(f"{mention} {resp}")
                    else:
                        # basic response
                        await message.channel.send(f"{resp}")


def add_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--token',
                        help='Specify the discord bot token',
                        dest='token',
                        type=str,
                        )

    parser.add_argument('-c', '--commands',
                        help=('Specify the location of'
                              'the commands JSON to load'),
                        dest='commandfile',
                        type=str,
                        default=('https://raw.githubusercontent.com/'
                                 'freqtrade/ft_discord_bot/master/'
                                 'bot_commands.json')
                        )
    args = parser.parse_args()
    return vars(args)


def main(args):
    intents = discord.Intents.default()
    intents.message_content = True

    client = ft_discord_command_bot(intents=intents)
    client.setup(args.get("commandfile"))
    client.load_commands()

    client.run(args.get("token"))


if __name__ == "__main__":
    args = add_arguments()
    main(args)
