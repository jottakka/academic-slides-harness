# Uso

O Academic Slides Harness é usado principalmente por tools MCP. A CLI atual é
para diagnósticos; geração, renderização, previews e validação acontecem pelo
servidor MCP local.

## Iniciar O Servidor MCP

```powershell
uv run python server.py stdio
```

Qualquer cliente MCP com suporte a stdio pode se conectar a esse processo. O
Arcade também pode iniciar o servidor a partir da raiz do repositório:

```powershell
arcade mcp stdio --cwd .
```

## Fluxo Básico De Tools

Use um diretório de saída fornecido pelo usuário, normalmente dentro de `runs/`.

1. Criar uma run:

```json
{
  "tool": "AcademicSlidesHarness_CreateRun",
  "arguments": {
    "base_dir": "runs",
    "title": "Image Processing Chapter 12"
  }
}
```

2. Inspecionar o PDF fonte:

```json
{
  "tool": "AcademicSlidesHarness_IngestSource",
  "arguments": {
    "source_path": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf"
  }
}
```

3. Extrair texto de páginas para planejamento:

```json
{
  "tool": "AcademicSlidesHarness_ExtractSourcePages",
  "arguments": {
    "source_pdf": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf",
    "pages": "1,3,5",
    "max_chars_per_page": 2000
  }
}
```

4. Renderizar previews do PDF fonte:

```json
{
  "tool": "AcademicSlidesHarness_RenderSourcePreview",
  "arguments": {
    "source_pdf": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf",
    "output_dir": "runs/image-processing-chapter-12/screenshots",
    "pages": "1,4",
    "resolution": "review"
  }
}
```

5. Renderizar um crop focado:

```json
{
  "tool": "AcademicSlidesHarness_RenderZoomCrop",
  "arguments": {
    "pdf_path": "tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf",
    "output_dir": "runs/image-processing-chapter-12/screenshots",
    "target": "source_pdf",
    "page": 4,
    "crop": {
      "x": 0.05,
      "y": 0.42,
      "width": 0.9,
      "height": 0.36,
      "normalized": true
    },
    "resolution": "review",
    "zoom": 2.5
  }
}
```

6. Criar um plano determinístico:

```json
{
  "tool": "AcademicSlidesHarness_PlanDeck",
  "arguments": {
    "title": "Image Processing Chapter 12",
    "excerpts": ["<trecho da pagina 1>", "<trecho da pagina 3>", "<trecho da pagina 5>"],
    "max_slides": 3
  }
}
```

7. Renderizar um deck Beamer de compatibilidade:

```json
{
  "tool": "AcademicSlidesHarness_RenderBeamer",
  "arguments": {
    "output_dir": "runs/image-processing-chapter-12/rendered",
    "title": "Image Processing Chapter 12",
    "slides": [
      {
        "title": "Image Processing",
        "bullets": ["Images become matrices", "Operations should be reproducible"]
      }
    ]
  }
}
```

Para o caminho visual mais rico, prefira
`AcademicSlidesHarness_RenderRichBeamer`.

## Workflow De Deck Visual Rico

Primeiro inspecione os layouts e o tema disponíveis:

```json
{ "tool": "AcademicSlidesHarness_ListThemePresets", "arguments": {} }
```

Leia estes resources MCP no seu cliente:

- `academic-slides://layouts/rich_slide_patterns`
- `academic-slides://schemas/rich_slide_plan`
- `academic-slides://prompts/draft_visual_academic_deck`
- `academic-slides://prompts/visual_quality_rubric`
- `academic-slides://prompts/didactic_quality_rubric`
- `academic-slides://themes/default_visual_academic`

Opcionalmente renderize placeholders de layout:

```json
{
  "tool": "AcademicSlidesHarness_RenderLayoutPlaceholders",
  "arguments": {
    "output_dir": "runs/image-processing-chapter-12/layout-placeholders",
    "layouts": "all",
    "overwrite": false
  }
}
```

Renderize Beamer rico:

```json
{
  "tool": "AcademicSlidesHarness_RenderRichBeamer",
  "arguments": {
    "output_dir": "runs/image-processing-chapter-12/rich-rendered",
    "title": "Image Processing Chapter 12",
    "slides": [
      {
        "title": "Pixels Become Measurements",
        "layout": "figure_explanation",
        "learning_goal": "Explain why a focused crop is better than a full page screenshot.",
        "blocks": [
          {
            "type": "visual",
            "artifact_path": "<absolute-path-to-source-crop-png>"
          },
          {
            "type": "claim",
            "text": "Focused visual evidence keeps the teaching point inspectable."
          },
          {
            "type": "source_citation",
            "source_page": 4
          }
        ]
      }
    ]
  }
}
```

O renderer rico copia assets visuais para o diretório do deck, sanitiza imagens,
checa limites de texto e rejeita warnings visuais fortes, exceto quando o slide
permite override explicitamente.

## Compilar E Gerar Previews

Compilar Beamer com Tectonic:

```json
{
  "tool": "AcademicSlidesHarness_CompileRenderedBeamer",
  "arguments": {
    "tex_path": "runs/image-processing-chapter-12/rich-rendered/deck.tex",
    "output_dir": "runs/image-processing-chapter-12/compiled"
  }
}
```

Renderizar previews dos slides:

```json
{
  "tool": "AcademicSlidesHarness_RenderSlidePreview",
  "arguments": {
    "deck_pdf": "runs/image-processing-chapter-12/compiled/deck.pdf",
    "output_dir": "runs/image-processing-chapter-12/screenshots",
    "slides": "1-3",
    "resolution": "review"
  }
}
```

Listar artifacts:

```json
{
  "tool": "AcademicSlidesHarness_ListVisualArtifacts",
  "arguments": {
    "screenshots_dir": "runs/image-processing-chapter-12/screenshots"
  }
}
```

Validar a run:

```json
{
  "tool": "AcademicSlidesHarness_ValidateRun",
  "arguments": {
    "run_dir": "runs/image-processing-chapter-12"
  }
}
```

## Outputs Em `runs/`

Outputs típicos:

- `manifest.json`: identidade e metadados da run.
- `screenshots/`: previews de fonte, previews de deck, crops e sidecars
  `.png.json`.
- `rendered/` ou `rich-rendered/`: `deck.tex` gerado e assets visuais copiados.
- `compiled/`: `deck.pdf` gerado quando Tectonic passa.

`runs/` é ignorado pelo git exceto por `runs/.gitkeep`.

## Fixture Real

O repositório inclui uma fixture real de capítulo open-access de processamento de
imagens:

```text
tests/fixtures/sources/springer-elements-robotics-ch12-image-processing.pdf
```

Ela é usada por testes end-to-end porque contém prosa acadêmica, figuras,
fórmulas e tabelas realistas. Veja `tests/fixtures/sources/README.md`.

## QA Visual

Tools visuais retornam metadados estruturados com paths absolutos, dimensões,
resolução, DPI, scale, zoom, alvo, página/slide, SHA-256 e warnings de qualidade.
Para figuras densas ou texto pequeno, prefira zoom crops em vez de apenas
previews de slide inteiro.

Presets de resolução:

- `fast`: iteração.
- `review`: QA normal.
- `print`: alta resolução quando necessário.

## Validação

Validação normal:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run pytest -m "not ollama and not arcade_live" -q
uv run academic-slides-harness doctor arcade --json
uv run pytest -m arcade_live -q
```

Opcional:

```powershell
uv run pytest tests/test_open_access_book_e2e.py -q
uv run pytest -m ollama -q
```
