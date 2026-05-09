# Local LLM and Deterministic Fallback Policy

The harness should work without any LLM provider.

- Use deterministic providers for core correctness and testability.
- Use Ollama for acceleration or analysis only when it is available and explicitly enabled by a live test or runtime setting.
- Keep local LLM outputs behind typed interfaces such as `DeckPlan`.
- Never skip ingestion, render, visual, or validation gates because an LLM produced plausible text.
- Prefer `nomic-embed-text` for local embedding checks when available.
- Prefer smaller local chat models for draft review and larger models only when the task benefits from them.

When a local model is unavailable, return a clear fallback result rather than failing a deterministic workflow.
