import pytest

from tirias.skill_system.gateway import SkillGateway
from tirias.skill_system.manager import SkillManager
from tirias.skill_system.system_skills import BrightnessSkill, MediaSkill, VolumeSkill

SINK = "@DEFAULT_AUDIO_SINK@"


def runner(calls, brightness="50%"):
    def run(command):
        calls.append(command)
        if command[:2] == ["brightnessctl", "-m"]:
            return f"intel_backlight,backlight,9600,{brightness},19200\n"
        return ""
    return run


def gateway_for(tmp_path, skill, granted):
    manager = SkillManager()
    ok, errors = manager.register_skill(skill)
    assert ok, errors
    assert manager.enable_skill(skill.manifest.skill_id)
    return SkillGateway(manager, granted, audit_path=tmp_path / "audit.log")


def test_media_next_track(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, MediaSkill(runner=runner(calls)), ("desktop.interact",))
    result = gw.request("media_control", "next_track", {})
    assert result.allowed and result.message == "Done: Next track."
    assert calls == [["playerctl", "next"]]


def test_media_denied_without_permission(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, MediaSkill(runner=runner(calls)), ())
    assert not gw.request("media_control", "pause", {}).allowed
    assert calls == []


def test_media_failure_is_reported(tmp_path):
    def broken(command):
        raise OSError("No players found")

    gw = gateway_for(tmp_path, MediaSkill(runner=broken), ("desktop.interact",))
    result = gw.request("media_control", "pause", {})
    assert result.message == "Failed: No players found"


def test_set_volume_caps_and_unmutes(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, VolumeSkill(runner=runner(calls)), ("system.manage",))
    result = gw.request("volume_control", "set_volume", {"level": 40})
    assert result.message == "Done: Volume set to 40 percent."
    assert calls == [
        ["wpctl", "set-volume", "-l", "1.0", SINK, "40%"],
        ["wpctl", "set-mute", SINK, "0"],
    ]


def test_change_volume_down(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, VolumeSkill(runner=runner(calls)), ("system.manage",))
    gw.request("volume_control", "change_volume", {"delta": -10})
    assert calls == [["wpctl", "set-volume", "-l", "1.0", SINK, "10%-"]]


def test_mute(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, VolumeSkill(runner=runner(calls)), ("system.manage",))
    gw.request("volume_control", "set_mute", {"muted": True})
    assert calls == [["wpctl", "set-mute", SINK, "1"]]


@pytest.mark.parametrize("action,arguments", [
    ("set_volume", {"level": 101}),
    ("set_volume", {"level": -1}),
    ("set_volume", {"level": "40"}),
    ("set_volume", {"level": True}),
    ("set_volume", {"level": 40, "extra": 1}),
    ("change_volume", {"delta": 80}),
    ("set_mute", {"muted": "yes"}),
])
def test_volume_rejects_bad_arguments(tmp_path, action, arguments):
    calls = []
    gw = gateway_for(tmp_path, VolumeSkill(runner=runner(calls)), ("system.manage",))
    assert not gw.request("volume_control", action, arguments).allowed
    assert calls == []


def test_volume_denied_without_permission(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, VolumeSkill(runner=runner(calls)), ())
    assert not gw.request("volume_control", "set_volume", {"level": 40}).allowed
    assert calls == []


def test_set_brightness(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, BrightnessSkill(runner=runner(calls)), ("system.manage",))
    gw.request("brightness_control", "set_brightness", {"percent": 70})
    assert calls == [["brightnessctl", "set", "70%"]]


def test_change_brightness_reads_then_sets(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, BrightnessSkill(runner=runner(calls, "50%")), ("system.manage",))
    result = gw.request("brightness_control", "change_brightness", {"delta": 10})
    assert result.message == "Done: Brightness set to 60 percent."
    assert calls == [["brightnessctl", "-m"], ["brightnessctl", "set", "60%"]]


def test_brightness_never_goes_below_minimum(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, BrightnessSkill(runner=runner(calls, "20%")), ("system.manage",))
    gw.request("brightness_control", "change_brightness", {"delta": -50})
    assert calls[-1] == ["brightnessctl", "set", "5%"]


def test_brightness_rejects_black_screen_and_overflow(tmp_path):
    calls = []
    gw = gateway_for(tmp_path, BrightnessSkill(runner=runner(calls)), ("system.manage",))
    assert not gw.request("brightness_control", "set_brightness", {"percent": 0}).allowed
    assert not gw.request("brightness_control", "set_brightness", {"percent": 101}).allowed
    assert calls == []
