# Arcade MCP Bug Report: CLI PATH and Local Engine Unavailable

## Summary

The current Windows environment has Arcade packages installed in the project venv, and the Arcade CLI can be installed with `uv tool install arcade-mcp`. After install, the executable is available at `C:\Users\fjlim\.local\bin\arcade.exe`, but that directory is not on the current PATH. The configured local engine and worker ports are also closed.

Correction: local Arcade MCP stdio work does not require the engine or worker
ports. The local path is `arcade mcp stdio --cwd .` or this repo's
`uv run python server.py stdio` entrypoint. Treat the port checks below as
HTTP-specific diagnostics, not as the default live-test gate.

## Reproduction

From `C:\Users\fjlim\Documents\Codex\academic-slides-harness`:

```powershell
where.exe arcade-mcp
uv run arcade-mcp --help
C:\Users\fjlim\.local\bin\arcade.exe --version
Test-NetConnection -ComputerName 127.0.0.1 -Port 9099
Test-NetConnection -ComputerName 127.0.0.1 -Port 8002
```

## Observed

- `where.exe arcade-mcp` does not find an executable until `C:\Users\fjlim\.local\bin` is added to PATH.
- `uv run arcade-mcp --help` fails with program not found.
- `C:\Users\fjlim\.local\bin\arcade.exe --version` works after `uv tool install arcade-mcp`.
- TCP checks for `127.0.0.1:9099` and `127.0.0.1:8002` fail.

## Expected

After installing Arcade MCP project dependencies, either the expected CLI should be available or documentation should identify the correct executable/module command. If local engine config points at `9099` and worker config points at `8002`, the startup workflow should make it clear how to launch both.

## Impact

- HTTP endpoint checks cannot run until the configured ports are open.
- Stdio-based `arcade_live` checks can run locally through the Arcade CLI without engine/worker endpoints.

## Suggested Fix

- Document the canonical Windows command for starting the Arcade MCP server from a `uv` project and make PATH setup explicit.
- Keep engine/worker health checks behind an explicit HTTP diagnostics flag.
- Validate the local `arcade mcp stdio` command path separately from HTTP endpoints.
