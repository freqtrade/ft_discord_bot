import argparse
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import discord
import rapidjson
import requests
from discord import app_commands
from requests.exceptions import ConnectionError
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ft_discord_command_bot")

allowed_managers = [
    "hippocritical.#0",
    "froggleston#0",
    "xmatthias#0",
    "stash86#0",
    "perkmeister#0",
    "joeschr#0",
    "freqai#0"
]


class ft_discord_command_bot(discord.Client):

    def __init__(self, *args, **kwargs):
        intents = kwargs.pop("intents", discord.Intents.default())
        super().__init__(intents=intents, *args, **kwargs)
        self._commandfile = None
        self.guild_id = None
        self.base_commands = {}
        self.rate_limited_calls = {}
        self._commands_registered = False
        self.search_base_url = 'https://www.freqtrade.io/en/latest/?q='
        self.gh_base_url = 'https://github.com/freqtrade/freqtrade/search?q='
        self.lmgtfy_base_url = 'https://letmegooglethat.com/?q='
        self.tree = app_commands.CommandTree(self)

    def setup(self, commandfile):
        self._commandfile = commandfile
        self.base_commands = {}
        self.rate_limited_calls = {}
        self.search_base_url = 'https://www.freqtrade.io/en/latest/?q='
        self.gh_base_url = 'https://github.com/freqtrade/freqtrade/search?q='
        self.lmgtfy_base_url = 'https://letmegooglethat.com/?q='

    def _version(self) -> str:
        return "1.00"

    async def setup_hook(self):
        if self.base_commands:
            self.register_commands()
        if self.guild_id:
            await self.tree.sync(guild=discord.Object(id=self.guild_id))
        else:
            await self.tree.sync()

    async def reload_commands(self):
        self.load_commands()
        return "Reloaded commands"

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)

    @staticmethod
    def _slash_name(command_name: str) -> str:
        cleaned = re.sub(r"[^a-z0-9]+", "-", command_name.lower()).strip("-")
        return cleaned or "command"

    def register_commands(self):
        if self._commands_registered:
            return

        self._commands_registered = True

        async def manager_only(interaction: discord.Interaction) -> bool:
            if str(interaction.user) not in allowed_managers:
                raise app_commands.CheckFailure(
                    "You are not allowed to use this command."
                )
            return True

        @self.tree.command(
            name="help",
            description="Show available bot helper commands",
        )
        async def help_command(
            interaction: discord.Interaction,
            user: discord.Member | None = None,
        ):
            response = f"```{self.print_commands()}```"
            if user is not None:
                response = f"{user.mention} {response}"
            await interaction.response.send_message(response)

        @self.tree.command(
            name="reload-commands",
            description="Reload the configured helper command list",
        )
        @app_commands.check(manager_only)
        async def reload_commands(
            interaction: discord.Interaction,
            user: discord.Member | None = None,
        ):
            await interaction.response.defer()
            try:
                await self.reload_commands()
            except Exception as exc:
                await interaction.followup.send(
                    f"Unable to reload commands: {exc}"
                )
                return

            response = "Reloaded commands"
            if user is not None:
                response = f"{user.mention} {response}"
            await interaction.followup.send(response)

        @self.tree.command(
            name="search",
            description="Search the Freqtrade documentation for a query",
        )
        async def search_command(
            interaction: discord.Interaction,
            query: str,
            user: discord.Member | None = None,
        ):
            response = self.process_search(query)
            if user is not None:
                response = f"{user.mention} {response}"
            await interaction.response.send_message(response)

        @self.tree.command(
            name="gh",
            description="Search GitHub for a query",
        )
        async def gh_command(
            interaction: discord.Interaction,
            query: str,
            user: discord.Member | None = None,
        ):
            response = self.process_gh(query)
            if user is not None:
                response = f"{user.mention} {response}"
            await interaction.response.send_message(response)

        @self.tree.command(
            name="lmgtfy",
            description="Create a 'Let me Google that for you' link",
        )
        async def lmgtfy_command(
            interaction: discord.Interaction,
            query: str,
            user: discord.Member | None = None,
        ):
            response = self.process_lmgtfy(query)
            if user is not None:
                response = f"{user.mention} {response}"
            await interaction.response.send_message(response)

        for command_name in sorted(self.base_commands.keys()):
            slash_name = self._slash_name(command_name)
            if slash_name in {"help", "reload-commands", "search", "gh", "lmgtfy"}:
                continue

            async def command_handler(
                interaction: discord.Interaction,
                user: discord.Member | None = None,
                command_key: str = command_name,
            ):
                response = self.base_commands.get(command_key)
                if not response:
                    await interaction.response.send_message(
                        f"No helper named '{command_key}' is currently configured."
                    )
                    return
                if user is not None:
                    response = f"{user.mention} {response}"
                await interaction.response.send_message(response)

            self.tree.command(
                name=slash_name,
                description=f"Show the '{command_name}' helper response",
            )(command_handler)

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
        else:
            return None

    def process_search(self, message):
        is_base = self.process_command(message)
        if is_base is not None:
            return is_base

        msg = message.replace(" ", "%20")
        full_url = f'{self.search_base_url}{msg}'
        return f'{self.base_commands["search"]}{full_url}'

    def process_gh(self, message):
        msg = message.replace(" ", "%20")
        full_url = f'{self.gh_base_url}{msg}'
        return f'{full_url}'

    def process_lmgtfy(self, message):
        msg = message.replace(" ", "%20")
        full_url = f'{self.lmgtfy_base_url}{msg}'
        return f'{full_url}'

    def _rate_limited(self, call=None, limit_sec=20):
        if call is not None:
            if self.rate_limited_calls[call] is not None:
                elapsed = datetime.now() - self.rate_limited_calls[call]
                if elapsed <= timedelta(seconds=limit_sec):
                    return True

            self.rate_limited_calls[call] = datetime.now()

        return False


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
    parser.add_argument('-g', '--guild-id',
                        help='Optional guild ID to register slash commands immediately',
                        dest='guild_id',
                        type=int,
                        default=None)
    args = parser.parse_args()
    return vars(args)


def main(args):
    client = ft_discord_command_bot()
    client.guild_id = args.get("guild_id")
    client.setup(args.get("commandfile"))
    client.load_commands()

    client.run(args.get("token"))


if __name__ == "__main__":
    args = add_arguments()
    main(args)
