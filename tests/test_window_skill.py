import pytest

from tirias.skill_system import window_skill
from tirias.skill_system.gateway import SkillGateway
from tirias.skill_system.manager import SkillManager
from tirias.skill_system.window_skill import WindowSkill, find_active_window, parse_window_request

WINDOWS = "0x04600003  0 kali Notes\n0x04800005  0 kali Terminal - raymond\n"


def fake_runner(calls, windows=WINDOWS, active="73400323", pid="4242"):
    def run(command):
        calls.append(command)
        if command[:2] == ["xdotool", "getactivewindow"]:
            return active + "\n"
        if command[:2] == ["xdotool", "getwindowpid"]:
            return pid + "\n"
        if command[:2] == ["wmctrl", "-l"]:
            return windows
        return ""
    return run


def make_gateway(tmp_path, runner, granted=("windows.control",)):
    manager = SkillManager()
    ok, errors = manager.register_skill(WindowSkill(runner=runner))
    assert ok, errors
    assert manager.enable_skill("window_control")
    return SkillGateway(manager, granted, audit_path=tmp_path / "audit.log")


def closes(calls):
    return [c for c in calls if c[:3] == ["wmctrl", "-i", "-c"]]


def test_find_active_window(monkeypatch):
    monkeypatch.setattr(window_skill, "_ancestor_pids", lambda: {1, 2})
    assert find_active_window(fake_runner([])) == ("0x04600003", "Notes")


def test_refuses_the_window_tirias_runs_in(monkeypatch):
    monkeypatch.setattr(window_skill, "_ancestor_pids", lambda: {4242})
    with pytest.raises(OSError, match="running in"):
        find_active_window(fake_runner([]))


def test_close_requires_confirmation_and_shows_the_title(tmp_path):
    calls = []
    gw = make_gateway(tmp_path, fake_runner(calls))
    result = gw.request("window_control", "close_window",
                        {"window_id": "0x04600003", "title": "Notes"})
    assert result.needs_confirmation and not result.allowed
    assert result.message == "Close the window 'Notes'?"
    assert closes(calls) == []


def test_confirmed_close_runs_once(tmp_path):
    calls = []
    gw = make_gateway(tmp_path, fake_runner(calls))
    result = gw.request("window_control", "close_window",
                        {"window_id": "0x04600003", "title": "Notes"}, confirmed=True)
    assert result.allowed and result.message == "Done: Asked 'Notes' to close."
    assert closes(calls) == [["wmctrl", "-i", "-c", "0x04600003"]]


def test_confirmed_but_title_changed_is_rejected(tmp_path):
    calls = []
    gw = make_gateway(tmp_path, fake_runner(calls))
    result = gw.request("window_control", "close_window",
                        {"window_id": "0x04600003", "title": "Something else"}, confirmed=True)
    assert result.message.startswith("Rejected: that window has changed")
    assert closes(calls) == []


def test_confirmed_but_window_gone_is_rejected(tmp_path):
    calls = []
    gw = make_gateway(tmp_path, fake_runner(calls, windows="0x04800005  0 kali Other\n"))
    result = gw.request("window_control", "close_window",
                        {"window_id": "0x04600003", "title": "Notes"}, confirmed=True)
    assert result.message.startswith("Rejected: that window no longer exists")
    assert closes(calls) == []


@pytest.mark.parametrize("arguments", [
    {"window_id": "abc", "title": "Notes"},
    {"window_id": "0x04600003"},
    {"window_id": "0x04600003", "title": ""},
    {"window_id": "0x04600003", "title": "Notes", "extra": 1},
    {"window_id": "0x04600003; rm -rf", "title": "Notes"},
])
def test_bad_arguments_are_denied(tmp_path, arguments):
    calls = []
    gw = make_gateway(tmp_path, fake_runner(calls))
    assert not gw.request("window_control", "close_window", arguments, confirmed=True).allowed
    assert closes(calls) == []


def test_denied_without_permission(tmp_path):
    calls = []
    gw = make_gateway(tmp_path, fake_runner(calls), granted=())
    result = gw.request("window_control", "close_window",
                        {"window_id": "0x04600003", "title": "Notes"}, confirmed=True)
    assert not result.allowed and not result.needs_confirmation
    assert closes(calls) == []


@pytest.mark.parametrize("text", [
    "close this window", "Close the window.", "please close window",
    "close the active window", "close my window",
])
def test_close_phrases(text):
    assert parse_window_request(text) is True


@pytest.mark.parametrize("text", [
    "close the door", "close all windows", "what is a window",
    "open a window", "close this window and shut down", "", None,
])
def test_other_phrases_do_not_match(text):
    assert parse_window_request(text) is False
