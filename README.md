# TIRIAS Core v0.7 — Hybrid foundation + wake phrase prototype

v0.7 preserves the v0.6 Control Center and adds an optional voice-first listener. The existing Python core remains in place while we establish a reliable interface before introducing native Rust/C++ components.

## Start the normal Control Center

```bash
cd ~/Downloads/tirias-core-v0.7
bash setup_voice.sh
bash run_control_center.sh
```

## Start wake phrase mode

Run this in a terminal from the project folder:

```bash
bash run_wake_listener.sh
```

Then say **“Hey TIRIAS”**, pause, and say a supported command such as **“What time is it?”**. You can also say the wake phrase and command in one utterance, e.g. “Hey TIRIAS, what time is it?” Recognition is local using the downloaded Vosk model.

Stop the listener at any time with **Ctrl+C**. The microphone stays active only while this process runs. The prototype does not save audio or upload it. It uses a software wake-phrase detector based on continuous speech recognition, not a dedicated low-power wake-word model, so CPU usage and false detections may be higher than a production design.

## Setup

If `.venv` and the Vosk model are not installed in this project, run:

```bash
bash setup_voice.sh
```

The setup script can reuse the model from a neighboring `tirias-core-v0.5` folder if present. If Tkinter is missing on Kali/Debian, install it without upgrading other packages:

```bash
sudo apt install --no-upgrade python3-tk
```

## What works today

- Existing typed commands, spoken responses, confirmation flow, and Control Center from v0.6.
- Optional wake phrase detection for “Hey TIRIAS” / “Okay TIRIAS”.
- A short command window after the wake phrase; recognized commands go through the existing allowlisted command router.
- Stop by Ctrl+C, releasing the microphone.

## What this is not yet

- Not yet a broad autonomous assistant; natural-language understanding currently maps only to a small reviewed set of supported goals.
- Not a dedicated low-power wake-word model.
- Not a Rust/C++ rewrite. We will add native components when profiling demonstrates a concrete need and the module boundary is clear.
- Not a Windows remote-control agent or bootable USB OS.


## Offline-first intelligence foundation

The intelligence integration is being developed on the `feature/intelligence-foundation`
branch. It adds:

- Optional local GGUF model inference through `TIRIAS_MODEL_PATH`.
- Bounded, temporary conversation context.
- Explicit local SQLite memory commands: `remember KEY as VALUE`,
  `recall KEY`, `forget KEY`, and `list memories`.
- Deterministic planning and allowlisted execution after existing command and
  confirmation routes.
- Fail-closed handling: model output must match a canonical goal; arbitrary
  shell commands and model-generated code are never executed.

The local model weights and `llama-cpp-python` runtime are not included or
installed automatically. Without a configured model, exact supported goals
still work and unknown requests are rejected.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py control_center.py wake_listener.py
```

See `ARCHITECTURE.md` for the hybrid design rationale.
