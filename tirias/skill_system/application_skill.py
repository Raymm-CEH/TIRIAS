"""Built-in application control skill for TIRIAS."""

from tirias.app_controller import AppController
from tirias.app_registry import get_application
from tirias.skill_system.interface import Skill, SkillManifest


class ApplicationSkill(Skill):
    """Launch applications approved by TIRIAS."""

    def __init__(self, controller=None):
        self.controller = controller or AppController()

    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            skill_id="application_control",
            name="Application Control",
            version="1.0.0",
            description="Launch applications approved by TIRIAS.",
            permissions=("applications.launch",),
        )

    def available_actions(self) -> tuple[str, ...]:
        return ("launch_application",)

    def execute(self, action: str, arguments: dict) -> str:
        if action != "launch_application":
            return "Rejected: unsupported application action."

        if not isinstance(arguments, dict):
            return "Rejected: arguments must be a dictionary."

        if set(arguments) != {"app_id"}:
            return "Rejected: provide only an app_id argument."

        app_id = arguments["app_id"]

        if not isinstance(app_id, str):
            return "Rejected: application ID must be text."

        app = get_application(app_id)

        if app is None:
            return "Rejected: application is not approved."

        return self.controller.launch(app.app_id)

    def action_specs(self) -> dict:
        from tirias.app_registry import list_applications
        from tirias.skill_system.interface import ActionSpec

        return {
            "launch_application": ActionSpec(
                permission="applications.launch",
                schema={
                    "type": "object",
                    "properties": {
                        "app_id": {
                            "type": "string",
                            "enum": [a.app_id for a in list_applications()],
                        }
                    },
                    "required": ["app_id"],
                    "additionalProperties": False,
                },
            )
        }
