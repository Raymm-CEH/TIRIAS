# TIRIAS Intelligence Architecture

## Goal

Build a local-first assistant that can understand varied natural-language
requests while keeping planning and computer control deterministic,
permission-controlled, and testable.

## Architecture layers

1. **Input adapters** — typed input and local speech recognition produce text.
2. **Conversation context** — a bounded in-memory window keeps recent turns for
   references such as "that folder". It is temporary and can be cleared.
3. **Local language model** — an optional GGUF model interprets wording and
   proposes one canonical intent. It never creates shell commands or code.
4. **Intent validator** — accepts only exact goals from a reviewed allowlist.
5. **Deterministic planner** — maps accepted goals to typed TaskPlan steps.
6. **Local memory** — SQLite stores only facts explicitly saved by the user.
   Raw conversations are not automatically stored.
7. **Permission layer** — actions that change files, settings, or system state
   must use the existing pending-action and confirmation mechanism.
8. **Allowlisted executor** — dispatches only registered actions; no arbitrary
   shell, eval, or model-generated command execution.
9. **Audit trail** — existing core audit events record supported actions.

## Data flow

    Voice / Text
        |
        v
    Session Context <----> Explicit Local Memory
        |
        v
    Optional Local GGUF Model
        |
        v
    Strict Intent Allowlist
        |
        v
    Deterministic Planner
        |
        v
    Permission / Confirmation
        |
        v
    Allowlisted Executor
        |
        v
    Local Computer

## Offline operation

The core and memory use Python's standard library. The optional inference
adapter uses llama-cpp-python and a GGUF model stored on the user's device.
No cloud service is required. If the model is absent or fails, supported
exact planner phrases still work and unknown requests are rejected safely.

## Memory policy

- Session context is bounded and disappears when the process ends.
- Persistent memory is opt-in through an explicit remember() call.
- Memory values are length-limited and stored using SQLite parameters.
- Users can recall, list, and delete saved entries.
- Do not store passwords, authentication tokens, or other secrets.

## Safety invariants

- Model output is untrusted input.
- The model may select only a canonical intent; it cannot select arbitrary
  action identifiers, paths, shell commands, or Python code.
- Planner output is a structured object, not executable text.
- Executor actions are registered in code and independently validated.
- Destructive or externally visible actions require a separate confirmation.
- Failure, invalid model output, or missing model must fail closed.

## Current implementation boundary

The core now wires the local model adapter, allowlisted intent mapping,
bounded session context, explicit SQLite memory commands, deterministic
planner, and allowlisted executor into the command loop. Existing exact
commands and confirmation/cancellation handling run before the intelligence
fallback. The optional GGUF model is still not installed or configured, and
the integrated test suite must be run on the target Kali setup before this
branch is considered ready.
