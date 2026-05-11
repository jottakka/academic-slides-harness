# Arcade MCP Bug Report: Local Config Contains Plaintext Secrets

## Summary

A local Arcade configuration file on this machine contains plaintext credential material. The values are not copied here.

## Reproduction

1. Open the local Arcade config file at `<local-arcade-config>\engine.yaml`.
2. Inspect the `llm` and `security` sections.
3. Observe that credential-like values are stored directly in YAML instead of being referenced through environment variables or a secret store.

## Expected

Local Arcade configuration should not require plaintext API keys or private key material in the config file.

## Actual

The config file includes credential-like values directly in the file.

## Impact

- Accidental disclosure risk through screenshots, logs, backups, or file sharing.
- Harder rotation and auditability.
- Higher risk when sharing repro bundles with maintainers.

## Suggested Fix

- Rotate the exposed credentials.
- Replace inline values with environment variable references such as `${env:OPENAI_API_KEY}`.
- Move private key material to a local secret store or generated dev-only path outside shared config.
- Add a startup validation warning when a config includes raw `sk-` style keys or PEM blocks.
- Add a secret-scan test for local example configs.

## Project Mitigation

The harness now provides a redacted local scan command:

```powershell
uv run academic-slides-harness doctor secrets --path <local-arcade-config>\engine.yaml --json
```

This command reports finding type, file path, and line number without printing
matched secret values. It does not rotate or remove exposed credentials; rotate
and externalize them separately.
