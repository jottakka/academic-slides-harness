# Arcade MCP Bug Report: CLI and Local Engine Unavailable

## Summary

The current Windows environment has Arcade packages installed in the project venv, but no `arcade-mcp` executable is available from PATH or via `uv run arcade-mcp`. The configured local engine and worker ports are also closed.

## Reproduction

From `C:\Users\fjlim\Documents\Codex\academic-slides-harness`:

```powershell
where.exe arcade-mcp
uv run arcade-mcp --help
Test-NetConnection -ComputerName 127.0.0.1 -Port 9099
Test-NetConnection -ComputerName 127.0.0.1 -Port 8002
```

## Observed

- `where.exe arcade-mcp` does not find an executable.
- `uv run arcade-mcp --help` fails with program not found.
- TCP checks for `127.0.0.1:9099` and `127.0.0.1:8002` fail.

## Expected

After installing Arcade MCP project dependencies, either the expected CLI should be available or documentation should identify the correct executable/module command. If local engine config points at `9099` and worker config points at `8002`, the startup workflow should make it clear how to launch both.

## Impact

- Live `arcade_live` tests cannot run.
- Agents can only perform in-process MCP registration checks until the engine/worker startup path is fixed.

## Suggested Fix

- Document the canonical Windows command for starting the Arcade MCP server from a `uv` project.
- Add a smoke test command that validates CLI availability, engine health, and worker health separately.
- Provide typed error messages when engine or worker endpoints are down.
