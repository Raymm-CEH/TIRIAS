import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import TIRIASCore
from tirias.skill_system.application_skill import ApplicationSkill
from tirias.skill_system.gateway import SkillGateway
from tirias.skill_system.manager import SkillManager

FIREFOX = "/usr/lib/firefox-esr/firefox-esr"


class QuietSpeech:
    available = True
    enabled = False

    def enable(self):
        return False

    def disable(self):
        pass

    def speak(self, text):
        return False


class QuietVoice:
    ready = True
    max_seconds = 10

    def status(self):
        return "test"


class BrowserGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.core = TIRIASCore(
            home=self.home,
            audit_path=self.home / "audit.log",
            speech=QuietSpeech(),
            voice_input=QuietVoice(),
        )
        self.gateway_log = self.home / "gateway-audit.log"

    def tearDown(self):
        self.temp.cleanup()

    def test_browser_launch_goes_through_gateway(self):
        with patch("tirias.app_controller.shutil.which", return_value=FIREFOX), \
             patch("tirias.app_controller.subprocess.Popen") as popen:
            result = self.core.launch("browser")
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], [FIREFOX])
        self.assertEqual(result, "Opening browser.")
        outcomes = [json.loads(line)["outcome"]
                    for line in self.gateway_log.read_text().splitlines()]
        self.assertEqual(outcomes, ["allowed"])

    def test_denied_by_gateway_never_starts_a_process(self):
        manager = SkillManager()
        manager.register_skill(ApplicationSkill())
        manager.enable_skill("application_control")
        self.core.gateway = SkillGateway(
            manager, granted_permissions=(), audit_path=self.gateway_log
        )
        with patch("tirias.app_controller.shutil.which", return_value=FIREFOX), \
             patch("tirias.app_controller.subprocess.Popen") as popen:
            result = self.core.launch("browser")
        popen.assert_not_called()
        self.assertIn("couldn't open", result)
        outcomes = [json.loads(line)["outcome"]
                    for line in self.gateway_log.read_text().splitlines()]
        self.assertEqual(outcomes, ["denied"])

    def test_open_firefox_routes_to_browser_launch(self):
        with patch.object(self.core, "launch", return_value="Opening browser.") as launch:
            self.core.handle_command("open firefox")
        launch.assert_called_once_with("browser")


if __name__ == "__main__":
    unittest.main()
