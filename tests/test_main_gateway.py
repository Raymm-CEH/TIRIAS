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


class SearchRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.core = TIRIASCore(
            home=self.home,
            audit_path=self.home / "audit.log",
            speech=QuietSpeech(),
            voice_input=QuietVoice(),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_search_command_goes_through_gateway(self):
        with patch("tirias.skill_system.web_skill._open_in_firefox") as opener:
            _, text = self.core.handle_command("open my browser and search for spotify")
        opener.assert_called_once_with("https://duckduckgo.com/?q=spotify")
        self.assertEqual(text, "Searching the web for spotify.")

    def test_normal_question_does_not_search(self):
        with patch("tirias.skill_system.web_skill._open_in_firefox") as opener:
            self.core.handle_command("what is a search engine")
        opener.assert_not_called()


class MigratedLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.core = TIRIASCore(
            home=self.home,
            audit_path=self.home / "audit.log",
            speech=QuietSpeech(),
            voice_input=QuietVoice(),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_terminal_and_settings_launch_through_gateway(self):
        for app, path in (
            ("terminal", "/usr/bin/x-terminal-emulator"),
            ("settings", "/usr/bin/xfce4-settings-manager"),
        ):
            with patch("tirias.app_controller.shutil.which", return_value=path), \
                 patch("tirias.app_controller.subprocess.Popen") as popen:
                result = self.core.launch(app)
            popen.assert_called_once()
            self.assertEqual(popen.call_args.args[0], [path])
            self.assertEqual(result, f"Opening {app}.")

    def test_files_launch_goes_through_folder_skill(self):
        with patch("tirias.skill_system.folder_skill._open_in_file_manager") as opener:
            result = self.core.launch("files", self.core.home)
        opener.assert_called_once_with(self.core.home)
        self.assertEqual(result, "Opening files.")

    def test_files_outside_home_is_denied(self):
        with patch("tirias.skill_system.folder_skill._open_in_file_manager") as opener:
            result = self.core.launch("files", "/etc")
        opener.assert_not_called()
        self.assertIn("couldn't open", result)

    def test_control_center_goes_through_gateway(self):
        with patch("tirias.skill_system.control_center_skill._open_control_center") as opener:
            result = self.core.launch("control-center")
        opener.assert_called_once()
        self.assertEqual(result, "Opening the TIRIAS Control Center.")

    def test_unknown_app_is_refused(self):
        self.assertIn("approved", self.core.launch("calculator"))


class SystemRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.core = TIRIASCore(
            home=self.home,
            audit_path=self.home / "audit.log",
            speech=QuietSpeech(),
            voice_input=QuietVoice(),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_volume_up_goes_through_gateway(self):
        with patch("tirias.skill_system.system_skills._run", return_value="") as run:
            _, text = self.core.handle_command("turn the volume up")
        run.assert_any_call(
            ["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "10%+"]
        )
        self.assertEqual(text, "Volume up.")

    def test_next_song_goes_through_gateway(self):
        with patch("tirias.skill_system.system_skills._run", return_value="") as run:
            _, text = self.core.handle_command("next song")
        run.assert_called_once_with(["playerctl", "next"])
        self.assertEqual(text, "Next track.")

    def test_plain_question_does_not_touch_the_system(self):
        with patch("tirias.skill_system.system_skills._run") as run:
            self.core.handle_command("what is a volume knob")
        run.assert_not_called()
