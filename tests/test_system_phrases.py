import pytest

from tirias.skill_system.system_phrases import parse_system_request


@pytest.mark.parametrize("text,expected", [
    ("turn the volume up", ("volume_control", "change_volume", {"delta": 10})),
    ("Louder!", ("volume_control", "change_volume", {"delta": 10})),
    ("please turn it down", ("volume_control", "change_volume", {"delta": -10})),
    ("quieter", ("volume_control", "change_volume", {"delta": -10})),
    ("set volume to 40", ("volume_control", "set_volume", {"level": 40})),
    ("volume 40 percent", ("volume_control", "set_volume", {"level": 40})),
    ("set the volume to 150", ("volume_control", "set_volume", {"level": 100})),
    ("mute", ("volume_control", "set_mute", {"muted": True})),
    ("unmute the sound", ("volume_control", "set_mute", {"muted": False})),
    ("brighter", ("brightness_control", "change_brightness", {"delta": 10})),
    ("make the screen dimmer", ("brightness_control", "change_brightness", {"delta": -10})),
    ("set brightness to 70", ("brightness_control", "set_brightness", {"percent": 70})),
    ("brightness to 0", ("brightness_control", "set_brightness", {"percent": 5})),
    ("pause the music", ("media_control", "pause", {})),
    ("resume", ("media_control", "play", {})),
    ("next song", ("media_control", "next_track", {})),
    ("skip", ("media_control", "next_track", {})),
    ("go back a song", ("media_control", "previous_track", {})),
])
def test_system_phrases_match(text, expected):
    assert parse_system_request(text) == expected


@pytest.mark.parametrize("text", [
    "what is the volume of a sphere",
    "search for volume up",
    "play a song by adele",
    "tell me about next week",
    "open my browser",
    "who is elon musk",
    "",
    None,
])
def test_conversation_is_not_a_system_command(text):
    assert parse_system_request(text) is None
