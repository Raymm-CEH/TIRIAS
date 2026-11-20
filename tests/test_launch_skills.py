import os

from tirias.skill_system.control_center_skill import ControlCenterSkill
from tirias.skill_system.folder_skill import FolderSkill
from tirias.skill_system.gateway import SkillGateway
from tirias.skill_system.manager import SkillManager


def gateway_for(skill, skill_id, permission, tmp_path):
    manager = SkillManager()
    ok, errors = manager.register_skill(skill)
    assert ok, errors
    assert manager.enable_skill(skill_id)
    return SkillGateway(manager, (permission,), audit_path=tmp_path / "audit.log")


def folder_setup(tmp_path):
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    opened = []
    skill = FolderSkill(home, opener=opened.append)
    return home, opened, gateway_for(skill, "folder_access", "files.read", tmp_path)


def test_opens_folder_inside_root(tmp_path):
    home, opened, gateway = folder_setup(tmp_path)
    result = gateway.request("folder_access", "open_folder", {"path": str(home / "Downloads")})
    assert result.allowed and result.message.startswith("Launch request sent")
    assert opened == [(home / "Downloads").resolve()]


def test_rejects_folder_outside_root(tmp_path):
    home, opened, gateway = folder_setup(tmp_path)
    result = gateway.request("folder_access", "open_folder", {"path": "/etc"})
    assert result.message.startswith("Rejected")
    assert opened == []


def test_rejects_dotdot_traversal(tmp_path):
    home, opened, gateway = folder_setup(tmp_path)
    result = gateway.request(
        "folder_access", "open_folder", {"path": str(home / "Downloads" / ".." / ".." / "..")}
    )
    assert result.message.startswith("Rejected")
    assert opened == []


def test_rejects_symlink_escape(tmp_path):
    home, opened, gateway = folder_setup(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, home / "link")
    result = gateway.request("folder_access", "open_folder", {"path": str(home / "link")})
    assert result.message.startswith("Rejected")
    assert opened == []


def test_denies_relative_path_and_extra_arguments(tmp_path):
    home, opened, gateway = folder_setup(tmp_path)
    assert not gateway.request("folder_access", "open_folder", {"path": "Downloads"}).allowed
    assert not gateway.request(
        "folder_access", "open_folder", {"path": str(home), "app": "evil"}
    ).allowed
    assert opened == []


def test_control_center_opens_existing_script(tmp_path):
    script = tmp_path / "control_center.py"
    script.write_text("# test")
    opened = []
    skill = ControlCenterSkill(script, opener=opened.append)
    gateway = gateway_for(skill, "control_center", "desktop.interact", tmp_path)
    result = gateway.request("control_center", "open_control_center", {})
    assert result.message.startswith("Launch request sent")
    assert opened == [script.resolve()]


def test_control_center_rejects_arguments_and_missing_script(tmp_path):
    script = tmp_path / "control_center.py"
    script.write_text("# test")
    opened = []
    skill = ControlCenterSkill(script, opener=opened.append)
    gateway = gateway_for(skill, "control_center", "desktop.interact", tmp_path)
    assert not gateway.request("control_center", "open_control_center", {"x": 1}).allowed

    missing = ControlCenterSkill(tmp_path / "nope.py", opener=opened.append)
    gateway = gateway_for(missing, "control_center", "desktop.interact", tmp_path)
    result = gateway.request("control_center", "open_control_center", {})
    assert result.message.startswith("Rejected")
    assert opened == []
