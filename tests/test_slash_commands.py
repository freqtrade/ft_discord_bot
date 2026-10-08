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


def test_reload_rebuilds_tree_after_loading_new_commands():
    client = ft_discord_command_bot()
    events = []

    def fake_clear_commands(**kwargs):
        events.append(kwargs.get("guild"))

    async def fake_sync(**kwargs):
        events.append(kwargs.get("guild"))

    class FakeCommandTree:
        def clear_commands(self, **kwargs):
            events.append(kwargs.get("guild"))

        async def sync(self, **kwargs):
            events.append(kwargs.get("guild"))

        def command(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    client.load_commands = lambda: events.append("load")
    client.register_commands = lambda: events.append("register")
    client.tree.clear_commands = fake_clear_commands
    client.tree.sync = fake_sync
    original_tree_ctor = bot_module.app_commands.CommandTree
    bot_module.app_commands.CommandTree = lambda client: FakeCommandTree()
    try:
        asyncio.run(client.reload_commands())
    finally:
        bot_module.app_commands.CommandTree = original_tree_ctor

    assert events == ["load", None, "register", None]
