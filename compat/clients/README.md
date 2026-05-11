# Client Config Templates

This directory contains portable client configuration examples for local MCP
stdio use.

`vscode-academic-slides-harness.json` assumes the client launches commands from
the repository root, so the command is equivalent to:

```powershell
uv run python server.py stdio
```

If you regenerate this file with Arcade or another client, review the diff before
committing. Generated client configs may embed absolute local paths to Python,
`uv`, the repository checkout, or a user profile directory. Keep those values out
of tracked public files.
