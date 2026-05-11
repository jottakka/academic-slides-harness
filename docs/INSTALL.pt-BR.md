# Instalação

Este guia descreve uma instalação local, sem depender de serviços pagos, para o
Academic Slides Harness. O projeto é um harness Python 3.13 e usa `uv` para
dependências e execução de comandos.

Superfície de comandos checada em 2026-05-11 a partir de `pyproject.toml`, help
da CLI e testes MCP stdio.

## Pré-requisitos

Obrigatórios:

- Python 3.13.
- `uv`.
- Git.

Recomendados:

- Tectonic, para compilar arquivos Beamer `.tex` gerados em PDF.
- Arcade CLI, para validar MCP stdio local.

Opcionais:

- Ollama, apenas para testes marcados com `ollama`. LLM local não é dependência
  de corretude.

## Clonar E Instalar

```powershell
git clone <repo-url>
cd academic-slides-harness
uv sync
```

`uv sync` instala o pacote do projeto e as dependências de desenvolvimento
declaradas em `pyproject.toml`.

## Sanity Checks

Rode os checks locais normais:

```powershell
uv run academic-slides-harness --help
uv run academic-slides-harness doctor --help
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
```

Cheque o Arcade antes de trabalho MCP live:

```powershell
uv run academic-slides-harness doctor arcade --json
```

Esse comando verifica se a Arcade CLI está disponível e se o entrypoint stdio
local `server.py` existe. Ele não exige portas HTTP locais antigas de engine ou
worker.

Se o Arcade estiver instalado fora do `PATH`, passe o caminho explicitamente:

```powershell
uv run academic-slides-harness doctor arcade --arcade-cli-path C:\path\to\arcade.exe --json
```

## MCP Stdio

Inicie o servidor MCP diretamente:

```powershell
uv run python server.py stdio
```

Se a Arcade CLI estiver no `PATH`, rode o wrapper stdio local a partir da raiz do
projeto:

```powershell
arcade mcp stdio --cwd .
```

Se a configuração de cliente estiver ausente ou desatualizada, gere uma config
Arcade compatível com VS Code:

```powershell
arcade configure vscode --transport stdio --entrypoint server.py --name academic-slides-harness --config compat\clients\vscode-academic-slides-harness.json
```

Rode o smoke live de MCP stdio:

```powershell
uv run pytest -m arcade_live -q
```

## Tectonic

Tectonic só é necessário para compilar Beamer `.tex` em PDF via
`AcademicSlidesHarness_CompileRenderedBeamer` ou testes que compilam LaTeX.

O harness procura o Tectonic nesta ordem:

1. `ACADEMIC_SLIDES_TECTONIC_PATH`
2. `TECTONIC_PATH`
3. um executável Tectonic empacotado pelo Codex, quando presente
4. `tectonic` no `PATH`

Exemplo em PowerShell:

```powershell
$env:ACADEMIC_SLIDES_TECTONIC_PATH = "C:\path\to\tectonic.exe"
uv run pytest tests/test_open_access_book_e2e.py -q
```

Se o Tectonic não estiver disponível, testes de compilação LaTeX podem ser
pulados ou tools de compilação podem retornar erro tipado.

## Notas Para Windows E PowerShell

- Rode os comandos a partir da raiz do repositório.
- Use aspas do PowerShell para markers do pytest:

```powershell
uv run pytest -m "not ollama and not arcade_live" -q
```

- Se `arcade` não for reconhecido, adicione a pasta da Arcade CLI ao `PATH` ou
  use `--arcade-cli-path`.
- Artifacts gerados devem ficar em `runs/` ou em outro diretório de saída
  fornecido pelo usuário. `runs/` é ignorado exceto por `runs/.gitkeep`.
- Não coloque tokens, API keys ou configs privadas em docs ou outputs gerados
  versionados.

## Troubleshooting

Falha no Arcade doctor:

- Rode `uv run academic-slides-harness doctor arcade --json`.
- Confirme que `server.py` existe na raiz do repo.
- Confirme que `arcade` está no `PATH` ou passe `--arcade-cli-path`.
- Use `--check-http-endpoints` somente quando estiver validando HTTP
  explicitamente.

Falha no teste MCP stdio:

- Rode novamente `uv sync`.
- Use `uv run pytest tests/test_mcp_stdio.py -q` para um check stdio mais
  restrito.
- Veja se a falha é dependência ausente, registro de tool ou startup do processo
  local.

Falha na compilação Tectonic:

- Confirme que Tectonic está instalado ou configurado em
  `ACADEMIC_SLIDES_TECTONIC_PATH`.
- Reexecute apenas o teste de compilação ou E2E depois de corrigir o caminho.

Secret scan:

```powershell
uv run academic-slides-harness doctor secrets --json
uv run academic-slides-harness doctor secrets --path docs --json
```
