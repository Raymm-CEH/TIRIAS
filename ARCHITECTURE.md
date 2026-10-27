# TIRIAS hybrid architecture — v0.7

TIRIAS is moving toward a hybrid design. This release keeps the proven Python command router and adds an opt-in ambient voice prototype. It does **not** yet introduce a Rust/C++ subsystem: language boundaries should be added when there is a measured need and a clear interface.

## Current layers

- **Voice prototype:** Vosk + sounddevice; local continuous speech recognition while `run_wake_listener.sh` is running.
- **Intelligence and orchestration:** Python command router (`main.py`). It recognizes a defined set of commands; this is not yet a general-purpose language model or open-ended planner.
- **Action boundary:** existing allowlisted command handlers; arbitrary shell commands are not executed.
- **Control Center:** existing GUI remains available for management; it is not required to keep the wake listener running.
- **Native components later:** consider Rust for a robust service/permission broker or C++ for measured performance-critical audio work. Keep the API narrow and benchmark before porting.

## Important prototype limitation

This is a **software wake-phrase prototype**, not a dedicated low-power wake-word detector. It runs Vosk continuously while enabled, which can use more CPU and can misrecognize phrases. It is opt-in: start it manually, and press `Ctrl+C` to stop and release the microphone. The app does not save or upload audio. Do not treat it as a production always-on service yet.
