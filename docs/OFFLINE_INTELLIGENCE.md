# TIRIAS Offline Intelligence Foundation

## Design

TIRIAS uses a local language model only to interpret natural-language requests
and suggest one canonical goal from a small allowlist. The model does not
produce shell commands, Python code, file paths, or executable steps.

The flow is:

1. Voice or typed input enters the existing command interface.
2. `IntelligenceEngine` asks the optional local model to select an allowed goal.
3. The returned JSON is parsed and checked against the exact allowlist.
4. The deterministic `Planner` creates a `TaskPlan`.
5. The separate `Executor` validates and runs only registered actions.
6. Existing confirmation handling remains mandatory for state-changing actions.

A missing model, invalid JSON, unknown goal, or inference error results in no
plan. Exact supported planner phrases continue to work without a model.

## Local model configuration

The model file is not committed to Git. Obtain a compatible GGUF instruction
model from a trusted source and store it locally. Set:

```bash
export TIRIAS_MODEL_PATH="$HOME/AI-Models/model.gguf"
```

Install the optional runtime inside the project's virtual environment:

```bash
python -m pip install llama-cpp-python
```

The runtime loads the model lazily. The core can still run without the optional
package or a model file.

## Safety boundary

Model output is untrusted. Only an exact canonical goal from
`IntelligenceEngine.ALLOWED_GOALS` is accepted. Planning and execution remain
separate. Do not connect model-generated text directly to a shell, eval,
subprocess command string, or unrestricted filesystem operation.

This is an initial intelligence foundation, not yet a general-purpose
autonomous agent. It does not claim long-term conversational memory or
independent reasoning beyond the supported task allowlist.
