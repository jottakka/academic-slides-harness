# Checklist De Release Pública

Use este checklist antes de abrir o repositório ao público ou convidar
colaboradores externos. Ele separa o que já está pronto do que ainda está
pendente.

Checado em 2026-05-11 contra a árvore atual do repositório.

## Básico Do Repositório

- [x] README público explica o projeto, status, quick start, uso MCP, comandos
  de validação, mapa de docs e política de artifacts gerados.
- [ ] `LICENSE` presente.
- [ ] `CONTRIBUTING.md` presente.
- [ ] `SECURITY.md` presente.
- [ ] `CODE_OF_CONDUCT.md` presente, se o projeto quiser expectativas de
  governança comunitária antes de colaboração pública.
- [ ] Templates de issue presentes.
- [ ] Template de pull request presente.

## Segurança E Secrets

- [x] `.gitignore` exclui runs geradas e artifacts comuns de Python/LaTeX/editor.
- [x] Docs evitam tokens e API keys.
- [x] Docs públicas usam placeholders para caminhos privados de executáveis.
- [x] `uv run academic-slides-harness doctor secrets --json` passou no readiness
  pass de 2026-05-11. Rode novamente antes do release final.
- [ ] Revisar `compat/clients/` para evitar paths locais ou credenciais antes de
  publicar.

## Instalação E Uso

- [x] Python 3.13 e `uv` documentados.
- [x] Tectonic documentado como necessário para compilação PDF.
- [x] Arcade CLI documentado como necessário para validação Arcade stdio.
- [x] Entrypoint MCP stdio documentado:
  `uv run python server.py stdio`.
- [x] Runner Arcade local documentado sem paths privados:
  `arcade mcp stdio --cwd .`.
- [x] Troubleshooting Windows/PowerShell documentado.

## Status Implementado

- [x] Features implementadas separadas de experimentais e planejadas.
- [x] Ingestão de vídeo marcada como planejada, não implementada.
- [x] Transporte HTTP marcado como opcional/experimental, não caminho live padrão.
- [x] Validação de deck visual rico descrita como em maturação, não completa.
- [x] `arcade_live` documentado como smoke local MCP stdio.

## Testes E Validação

Antes do release, rode e registre:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Checks adicionais recomendados:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run academic-slides-harness doctor secrets --json
```

Rode `uv run pytest -m ollama -q` somente quando participação do Ollama local for
esperada.

Readiness pass mais recente, 2026-05-11:

- `uv run ruff format --check .`: passou.
- `uv run ruff check .`: passou.
- `uv run pytest -m "not ollama and not arcade_live" -q`: passou, 123 passed e
  2 deselected.
- `uv run academic-slides-harness doctor arcade --json`: passou.
- `uv run pytest -m arcade_live -q`: passou, 1 passed e 124 deselected.
- `uv run academic-slides-harness doctor secrets --json`: passou.

## Limitações Conhecidas Para Manter Públicas

- A CLI hoje é apenas diagnóstica. A geração é MCP-first.
- Renderização visual rica existe, mas validação determinística de qualidade no
  nível do deck ainda está planejada.
- Tectonic precisa estar instalado ou configurado para compilar PDFs.
- Runs geradas não devem ser commitadas.
- Release público ainda precisa de decisões de licença e governança de
  contribuição.

## Clareza De Roadmap

- [x] Docs de design atuais identificam o trabalho de deck visual rico.
- [x] Plano de remediação visual documenta trabalho recente de qualidade e a
  necessidade do próximo validador.
- [ ] Consolidar wording antigo do roadmap antes de um anúncio público maior, se
  o repo precisar parecer mais polido que MVP readiness.
