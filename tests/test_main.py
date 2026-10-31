import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import (SpeechOutput, TIRIASCore, VoiceInput, is_listen_request, dispatch_voice_transcript, VoiceInputError)


class FakeSpeechOutput:
    def __init__(self):
        self.available = True
        self.enabled = True
        self.spoken = []

    def enable(self):
        self.enabled = self.available
        return self.enabled

    def disable(self):
        self.enabled = False

    def speak(self, text):
        if self.enabled and self.available:
            self.spoken.append(text)
            return True
        return False


class FakeVoiceInput:
    ready = True
    max_seconds = 10

    def status(self):
        return "Voice input: ready for tests."

    def list_devices(self):
        return "Available microphone inputs:\n  [0] Test Microphone (inputs: 1)"

    def listen_once(self):
        return "what time is it"


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        (self.home / "Downloads").mkdir()
        (self.home / "Documents").mkdir()
        (self.home / "sample.txt").write_text("test", encoding="utf-8")
        self.core = TIRIASCore(home=self.home, audit_path=self.home / "audit.log", speech=FakeSpeechOutput(), voice_input=FakeVoiceInput())

    def tearDown(self):
        self.temp.cleanup()

    def test_help_mentions_natural_language(self):
        keep, text = self.core.handle_command("what can you do for me?")
        self.assertTrue(keep)
        self.assertIn("natural-language", text)

    def test_natural_language_time(self):
        keep, text = self.core.handle_command("Please, tell me the time")
        self.assertTrue(keep)
        self.assertIn("The system time is", text)

    def test_status_reports_v06_and_voice_state(self):
        _, text = self.core.handle_command("show me system info")
        self.assertIn("v0.8-intelligence", text)
        self.assertIn("Spoken responses: on", text)

    def test_where_am_i_alias(self):
        _, text = self.core.handle_command("what folder am I in?")
        self.assertIn(str(self.home), text)

    def test_natural_navigation_to_downloads(self):
        _, text = self.core.handle_command("take me to my downloads")
        self.assertEqual(self.core.current_dir, (self.home / "Downloads").resolve())
        self.assertIn("current folder is now", text)

    def test_navigation_missing_folder_does_not_change_directory(self):
        before = self.core.current_dir
        _, text = self.core.handle_command("go to my pictures")
        self.assertEqual(self.core.current_dir, before)
        self.assertIn("don't recognize", text)

    def test_show_downloads_opens_only_known_path(self):
        with patch.object(self.core, "launch", return_value="Opening files.") as launch:
            _, text = self.core.handle_command("show me my downloads")
        launch.assert_called_once_with("files", (self.home / "Downloads").resolve())
        self.assertIn("Opening files", text)
        self.assertEqual(self.core.current_dir, (self.home / "Downloads").resolve())

    def test_list_files_natural_language(self):
        _, text = self.core.handle_command("show me what's in this folder")
        self.assertIn("sample.txt", text)

    def test_disk_space_natural_language(self):
        _, text = self.core.handle_command("How much space do I have left?")
        self.assertIn("GiB free", text)

    def test_launch_browser_alias_uses_allowlist(self):
        with patch.object(self.core, "launch", return_value="Opening browser.") as launch:
            _, text = self.core.handle_command("please launch my browser")
        launch.assert_called_once_with("browser")
        self.assertEqual(text, "Opening browser.")

    def test_open_terminal_alias(self):
        with patch.object(self.core, "launch", return_value="Opening terminal.") as launch:
            _, text = self.core.handle_command("start a terminal")
        launch.assert_called_once_with("terminal")
        self.assertEqual(text, "Opening terminal.")

    def test_create_folder_with_called_phrase_requires_confirmation(self):
        _, text = self.core.handle_command("Create a folder called Projects")
        self.assertIn("Type 'confirm'", text)
        self.assertFalse((self.home / "TIRIAS-Workspace" / "Projects").exists())

    def test_natural_confirmation_creates_pending_folder(self):
        self.core.handle_command("make a new folder named Demo")
        _, text = self.core.handle_command("yes please")
        self.assertIn("Created folder", text)
        self.assertTrue((self.home / "TIRIAS-Workspace" / "Demo").is_dir())

    def test_cancel_prevents_change(self):
        self.core.handle_command("new folder called Demo")
        _, text = self.core.handle_command("never mind")
        self.assertIn("No changes", text)
        self.assertFalse((self.home / "TIRIAS-Workspace" / "Demo").exists())

    def test_blocks_path_traversal(self):
        _, text = self.core.handle_command("create a folder called ../oops")
        self.assertIn("simple folder name", text)
        self.assertIsNone(self.core.pending)

    def test_arbitrary_shell_not_executed(self):
        _, text = self.core.handle_command("touch should_not_exist")
        self.assertIn("never execute arbitrary", text)
        self.assertFalse((self.home / "should_not_exist").exists())

    def test_command_injection_does_not_launch_browser(self):
        with patch.object(self.core, "launch") as launch:
            _, text = self.core.handle_command("open browser; touch injected")
        launch.assert_not_called()
        self.assertIn("don't recognize", text)
        self.assertFalse((self.home / "injected").exists())

    def test_confirmation_without_pending_action_does_nothing(self):
        _, text = self.core.handle_command("go ahead")
        self.assertIn("no pending action", text)

    def test_quit_alias_exits_only_tirias(self):
        keep, text = self.core.handle_command("goodbye")
        self.assertFalse(keep)
        self.assertIn("Goodbye", text)


    def test_voice_off_disables_spoken_responses(self):
        _, text = self.core.handle_command("turn voice off")
        self.assertIn("disabled", text)
        self.assertFalse(self.core.speech.enabled)

    def test_voice_on_enables_spoken_responses(self):
        self.core.handle_command("voice off")
        _, text = self.core.handle_command("please turn on voice")
        self.assertIn("enabled", text)
        self.assertTrue(self.core.speech.enabled)

    def test_voice_status_reports_state(self):
        self.core.handle_command("voice off")
        _, text = self.core.handle_command("speech status")
        self.assertIn("Speech engine: available", text)
        self.assertIn("Spoken responses: off", text)

    def test_speech_output_uses_stdin_without_shell(self):
        speech = SpeechOutput(binary="/fake/espeak-ng", enabled=True)
        completed = type("Completed", (), {"returncode": 0})()
        with patch("main.subprocess.run", return_value=completed) as run:
            self.assertTrue(speech.speak("hello TIRIAS"))
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["/fake/espeak-ng", "-v", "en-us", "-s", "165", "--stdin"])
        self.assertEqual(kwargs["input"], "hello TIRIAS")
        self.assertNotIn("shell", kwargs)

    def test_speech_output_shortens_long_responses(self):
        response = "word " * 100
        prepared = SpeechOutput.prepare_text(response)
        self.assertLessEqual(len(prepared), 300)
        self.assertIn("More details are displayed on screen", prepared)


    def test_voice_input_status_command(self):
        _, text = self.core.handle_command("voice input status")
        self.assertIn("Voice input: ready", text)

    def test_voice_devices_command(self):
        _, text = self.core.handle_command("list microphones")
        self.assertIn("Test Microphone", text)

    def test_listen_command_in_core_explains_interactive_flow(self):
        _, text = self.core.handle_command("listen")
        self.assertIn("interactive loop", text)

    def test_listen_phrases_are_explicit(self):
        self.assertTrue(is_listen_request("listen"))
        self.assertTrue(is_listen_request("Please, listen for a command."))
        self.assertTrue(is_listen_request("push to talk"))
        self.assertFalse(is_listen_request("please tell me the time"))

    def test_voice_transcript_uses_existing_command_router(self):
        keep, text = dispatch_voice_transcript(self.core, "what time is it")
        self.assertTrue(keep)
        self.assertIn("The system time is", text)

    def test_empty_voice_transcript_does_not_act(self):
        before = self.core.current_dir
        keep, text = dispatch_voice_transcript(self.core, " ")
        self.assertTrue(keep)
        self.assertIn("didn't catch", text)
        self.assertEqual(before, self.core.current_dir)

    def test_voice_transcript_never_executes_shell_text(self):
        with patch.object(self.core, "launch") as launch:
            keep, text = dispatch_voice_transcript(self.core, "open browser; touch injected")
        self.assertTrue(keep)
        launch.assert_not_called()
        self.assertIn("never execute arbitrary", text)
        self.assertFalse((self.home / "injected").exists())

    def test_missing_voice_model_reports_setup_needed(self):
        voice_input = VoiceInput(model_path=self.home / "missing-model")
        self.assertFalse(voice_input.ready)
        self.assertIn("setup needed", voice_input.status())
        with self.assertRaises(VoiceInputError):
            voice_input.listen_once()

    def test_status_includes_voice_input_state(self):
        _, text = self.core.handle_command("status")
        self.assertIn("Voice input: ready", text)

    def test_open_control_center_uses_allowlisted_launcher(self):
        with patch.object(self.core, "launch", return_value="Opening the TIRIAS Control Center.") as launch:
            keep, text = self.core.handle_command("open control center")
        self.assertTrue(keep)
        launch.assert_called_once_with("control-center")
        self.assertIn("Control Center", text)

    def test_help_mentions_control_center(self):
        _, text = self.core.handle_command("help")
        self.assertIn("Open Control Center", text)
\n
    def test_intelligence_fallback_plans_workspace_request(self):
        _, text = self.core.handle_command("inspect my workspace")
        self.assertIn("current folder is now", text)
        self.assertIn("Contents of", text)
        self.assertEqual(self.core.current_dir, self.core.workspace.resolve())

    def test_context_tracks_recent_command_and_response(self):
        self.core.handle_command("what time is it")
        turn = self.core.context.recent()[-1]
        self.assertEqual(turn.user, "what time is it")
        self.assertIn("The system time is", turn.assistant)

    def test_explicit_memory_can_be_saved_recalled_and_forgotten(self):
        _, saved = self.core.handle_command("remember preferred editor as vim")
        self.assertIn("remember preferred editor locally", saved)
        _, recalled = self.core.handle_command("recall preferred editor")
        self.assertIn("vim", recalled)
        _, forgotten = self.core.handle_command("forget preferred editor")
        self.assertIn("Forgot", forgotten)
        self.assertIsNone(self.core.memory.recall("preferred editor"))

    def test_memory_rejects_authentication_secrets(self):
        _, text = self.core.handle_command("remember password as example123")
        self.assertIn("won't store", text)
        self.assertIsNone(self.core.memory.recall("password"))

    def test_unknown_request_does_not_execute_model_supplied_command(self):
        class UnsafeModel:
            def generate(self, prompt):
                return '{"goal": "run_shell"}'
        core = TIRIASCore(
            home=self.home,
            audit_path=self.home / "audit.log",
            speech=FakeSpeechOutput(),
            voice_input=FakeVoiceInput(),
            model=UnsafeModel(),
            memory_path=self.home / "memory.sqlite3",
        )
        with patch.object(core, "launch") as launch:
            _, text = core.handle_command("do something unusual")
        launch.assert_not_called()
        self.assertIn("don't recognize", text)



if __name__ == "__main__":
    unittest.main()
