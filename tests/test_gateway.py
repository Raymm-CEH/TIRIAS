import json

from tirias.skill_system.application_skill import ApplicationSkill
from tirias.skill_system.gateway import SkillGateway
from tirias.skill_system.manager import SkillManager


class FakeController:
    def __init__(self):
        self.launched = []

    def launch(self, app_id):
        self.launched.append(app_id)
        return f"launched {app_id}"


def build(tmp_path, granted=("applications.launch",), enable=True):
    controller = FakeController()
    manager = SkillManager()
    ok, errors = manager.register_skill(ApplicationSkill(controller=controller))
    assert ok, errors
    if enable:
        assert manager.enable_skill("application_control")
    audit = tmp_path / "audit.log"
    return SkillGateway(manager, granted, audit_path=audit), controller, audit


def test_allows_valid_launch(tmp_path):
    gateway, controller, _ = build(tmp_path)
    result = gateway.request("application_control", "launch_application",
                             {"app_id": "firefox"})
    assert result.allowed
    assert controller.launched == ["firefox"]


def test_denies_when_permission_not_granted(tmp_path):
    gateway, controller, _ = build(tmp_path, granted=())
    result = gateway.request("application_control", "launch_application",
                             {"app_id": "firefox"})
    assert not result.allowed
    assert controller.launched == []


def test_denies_unapproved_app(tmp_path):
    gateway, controller, _ = build(tmp_path)
    result = gateway.request("application_control", "launch_application",
                             {"app_id": "rm -rf /"})
    assert not result.allowed
    assert controller.launched == []


def test_denies_extra_arguments(tmp_path):
    gateway, controller, _ = build(tmp_path)
    result = gateway.request("application_control", "launch_application",
                             {"app_id": "firefox", "flags": "--evil"})
    assert not result.allowed
    assert controller.launched == []


def test_denies_disabled_skill(tmp_path):
    gateway, controller, _ = build(tmp_path, enable=False)
    result = gateway.request("application_control", "launch_application",
                             {"app_id": "firefox"})
    assert not result.allowed


def test_denies_unknown_action(tmp_path):
    gateway, controller, _ = build(tmp_path)
    result = gateway.request("application_control", "delete_everything", {})
    assert not result.allowed


def test_audit_records_allowed_and_denied(tmp_path):
    gateway, _, audit = build(tmp_path)
    gateway.request("application_control", "launch_application", {"app_id": "firefox"})
    gateway.request("application_control", "launch_application", {"app_id": "nope"})
    outcomes = [json.loads(line)["outcome"] for line in audit.read_text().splitlines()]
    assert outcomes == ["allowed", "denied"]
