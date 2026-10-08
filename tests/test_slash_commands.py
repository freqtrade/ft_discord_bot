import inspect

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
