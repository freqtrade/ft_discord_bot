from ft_discord_bot.ft_discord_command_bot import ft_discord_command_bot


def test_bot_uses_default_non_privileged_intents_and_tree():
    client = ft_discord_command_bot()

    assert client.intents.message_content is False
    assert hasattr(client, "tree")
