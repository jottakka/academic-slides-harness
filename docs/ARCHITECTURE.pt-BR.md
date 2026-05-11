# Arquitetura E Tools MCP

O Academic Slides Harness é um sistema determinístico, LaTeX-first, para gerar
slides acadêmicos a partir de PDFs fonte. Ele foi desenhado para que um agente
possa planejar e renderizar um deck mantendo artifacts intermediários
inspecionáveis.

## Fronteiras Do Sistema

- `src/academic_slides_harness/core`: modelos Pydantic, hashes, manifests de
  run, definições de state machine e contratos de resultado.
- `src/academic_slides_harness/ingest`: inspeção de PDF e extração de texto por
  página.
- `src/academic_slides_harness/render`: renderização Beamer, layouts visuais
  ricos, presets de tema e compilação com Tectonic.
- `src/academic_slides_harness/visualize`: previews PDF-para-PNG, zoom crops,
  opções de renderização, sanitização de imagem e métricas visuais
  determinísticas.
- `src/academic_slides_harness/llm`: adapters opcionais, discovery redigido de
  providers e fallback determinístico.
- `src/academic_slides_harness/mcp`: construção do app Arcade MCP, registro de
  tools, resources, outputs estruturados e erros tipados.

Código de produção fica em `src/academic_slides_harness`. Testes ficam em
`tests`. Runs geradas devem ficar em `runs/` ou em outro diretório de saída
fornecido pelo chamador.

## Pipeline

O pipeline pretendido é:

```text
criar run
  -> ingerir PDF fonte
  -> extrair texto de páginas selecionadas
  -> renderizar previews e crops da fonte
  -> planejar conteúdo dos slides
  -> renderizar Beamer ou Beamer rico
  -> compilar PDF com Tectonic
  -> renderizar previews e crops do deck
  -> listar artifacts visuais
  -> validar run
```

O modelo de estado do pipeline é:

```text
created -> ingesting -> ingested -> planning -> planned -> rendering -> rendered
-> visualizing -> visualized -> validating -> validated|failed
```

O estado de execução de tools é:

```text
idle -> received -> eliciting|running -> progress -> completed|tool_error|fatal_error
```

A implementação atual expõe tools, resources, prompts, outputs estruturados e
erros tipados. Comportamento completo de tasks/progress/elicitation ainda é
direção de design, não uma promessa pública pronta.

## Transporte MCP

O entrypoint local estável é stdio:

```powershell
uv run python server.py stdio
```

`server.py` inicia `academic_slides_harness.mcp.server:main`. O servidor aceita
`stdio` por padrão e também aceita `http`, mas stdio é o caminho validado.

O Arcade pode rodar o servidor stdio a partir da raiz do repo:

```powershell
arcade mcp stdio --cwd .
```

Checks de endpoints HTTP são diagnósticos opcionais:

```powershell
uv run academic-slides-harness doctor arcade --check-http-endpoints --json
```

## Catálogo De Tools MCP

Geração e gestão de run:

- `AcademicSlidesHarness_CreateRun`: cria diretório de run, pasta de screenshots
  e `manifest.json`.
- `AcademicSlidesHarness_ValidateRun`: valida diretório de run, pasta de
  screenshots e schema do manifest.

Ingestão e planejamento:

- `AcademicSlidesHarness_IngestSource`: inspeciona um PDF e retorna metadados.
- `AcademicSlidesHarness_ExtractSourcePages`: retorna trechos de texto de
  páginas selecionadas.
- `AcademicSlidesHarness_ListModelProviders`: reporta disponibilidade redigida
  de providers/modelos locais ou configurados para escolher entre rotas
  deterministicas e assistidas por modelo.
- `AcademicSlidesHarness_PlanDeck`: cria plano determinístico a partir de
  trechos de texto usando o provider fallback.

Renderização e compilação:

- `AcademicSlidesHarness_RenderBeamer`: renderiza Beamer v0 de compatibilidade a
  partir de slides simples.
- `AcademicSlidesHarness_RenderRichBeamer`: renderiza slides ricos tipados com
  blocos visuais, citações, limites de texto, assets sanitizados e layouts ricos.
- `AcademicSlidesHarness_CompileRenderedBeamer`: compila `.tex` gerado com
  Tectonic.

Artifacts visuais:

- `AcademicSlidesHarness_RenderSourcePreview`: renderiza páginas do PDF fonte em
  PNG.
- `AcademicSlidesHarness_RenderSlidePreview`: renderiza páginas do deck
  compilado em PNG.
- `AcademicSlidesHarness_RenderZoomCrop`: renderiza um crop focado de PDF fonte
  ou deck.
- `AcademicSlidesHarness_ListVisualArtifacts`: lista PNGs e metadados.

Helpers de deck rico:

- `AcademicSlidesHarness_RenderLayoutPlaceholders`: gera previews PNG de
  placeholders para layouts ricos.
- `AcademicSlidesHarness_ListThemePresets`: lista presets determinísticos de
  tema visual.

## Catálogo De Resources MCP

Resources públicos atuais:

- `academic-slides://layouts/rich_slide_patterns`
- `academic-slides://schemas/rich_slide_plan`
- `academic-slides://prompts/draft_visual_academic_deck`
- `academic-slides://prompts/review_slide_validation`
- `academic-slides://prompts/review_visual_artifacts`
- `academic-slides://prompts/visual_quality_rubric`
- `academic-slides://prompts/didactic_quality_rubric`
- `academic-slides://themes/default_visual_academic`

Esses resources orientam agentes a produzir decks visuais com evidência em vez
de decks genéricos de bullet summary.

## Contrato De Artifacts

Tools visuais MCP devem retornar dados estruturados com:

- path absoluto do artifact;
- largura e altura;
- alvo (`source_pdf` ou `deck_pdf`);
- página ou slide;
- preset de resolução;
- DPI, scale e zoom;
- hash SHA-256;
- metadados e warnings de qualidade quando disponíveis.

Sidecars usam `.png.json` ao lado dos PNGs gerados. Chamadores devem preferir os
metadados do sidecar antes de inferir dados pelo nome do arquivo.

## Contrato De Erros

Tools retornam erros tipados em vez de vazar exceções internas quando possível.
Exemplos:

- `missing_input`
- `invalid_page_selection`
- `invalid_crop`
- `invalid_render_options`
- `artifact_exists`
- `validation_failed`
- `compile_failed`
- `compile_timeout`
- `invalid_visual_artifact`
- `image_too_small`
- `visual_quality_failed`
- `text_overflow_risk`

Isso permite que agentes recuperem o fluxo ou escolham um próximo passo mais
restrito.

## Implementado, Experimental, Planejado

Implementado:

- Ingestão de PDF e extração de texto por página.
- Renderização Beamer simples e rica.
- Compilação Tectonic quando o executável está disponível.
- Previews de fonte/deck, zoom crops, listagem de artifacts, hashes, sidecars e
  warnings de qualidade visual.
- Tools/resources MCP stdio com erros tipados.
- Diagnósticos locais de Arcade, providers/modelos e secrets.

Experimental:

- Gates de qualidade de deck visual rico. Vários warnings visuais já existem,
  mas um validador determinístico completo no nível do deck ainda está planejado.
- Transporte HTTP e checks de endpoints HTTP.

Planejado:

- Ingestão de vídeo.
- Arquivos públicos de governança, contribuição e segurança.

## Matriz De Validação

Gate local normal:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
```

Gate MCP/Arcade:

```powershell
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Gates opcionais:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run pytest -m ollama -q
uv run academic-slides-harness doctor models --json
uv run academic-slides-harness doctor secrets --json
```

`arcade_live` significa smoke local de runtime MCP stdio. Não é check de worker
ou engine HTTP.
