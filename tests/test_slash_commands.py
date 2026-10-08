import asyncio
import inspect

from ft_discord_bot import ft_discord_command_bot as bot_module
from ft_discord_bot.ft_discord_command_bot import ft_discord_command_bot


def test_bot_uses_default_non_privileged_intents_and_tree():
    client = ft_discord_command_bot()

    assert client.intents.message_content is False
    assert hasattr(client, "tree")


def test_helper_command_handler_accepts_optional_user():
    client = ft_discord_command_bot()
    client.base_commands = {"backtesting": "hello"}
    captured = {}

    def fake_command(*args, **kwargs):
        def decorator(func):
            captured["func"] = func
            return func

        return decorator

    client.tree.command = fake_command
    client.register_commands()

    sig = inspect.signature(captured["func"])
    assert "user" in sig.parameters
    assert sig.parameters["user"].default is None


def test_reload_refreshes_data_without_re_registering_commands():
    client = ft_discord_command_bot()
    events = []

    def fake_clear_commands(**kwargs):
        events.append("clear")

    async def fake_sync(**kwargs):
        events.append("sync")

    class FakeCommandTree:
        def clear_commands(self, **kwargs):
            events.append("clear")

        async def sync(self, **kwargs):
            events.append("sync")

        def command(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    client.load_commands = lambda: events.append("load")
    client.tree.clear_commands = fake_clear_commands
    client.tree.sync = fake_sync

    asyncio.run(client.reload_commands())

    assert events == ["load"]
