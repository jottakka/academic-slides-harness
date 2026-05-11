import json
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

from academic_slides_harness.ingest.pdf import normalize_extracted_pdf_text
from academic_slides_harness.mcp.server import (
    MCP_RESOURCE_URIS,
    MCP_TOOL_NAMES,
    build_app,
    compile_rendered_beamer,
    create_run,
    extract_source_pages,
    ingest_source,
    list_model_providers,
    list_theme_presets,
    list_visual_artifacts,
    plan_deck,
    render_beamer,
    render_layout_placeholders,
    render_rich_beamer,
    render_slide_preview,
    render_source_preview,
    render_zoom_crop,
    validate_layout_overflow,
    validate_run,
)
from academic_slides_harness.render.theme import ThemePresetError


def _make_pdf(path: Path) -> Path:
    doc = fitz.open()
    page = doc.new_page(width=200, height=120)
    page.insert_text((36, 60), "Academic Slides Harness", fontsize=12)
    doc.save(path)
    doc.close()
    return path


def _make_png(path: Path, *, width: int = 64, height: int = 48) -> Path:
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), False)
    pixmap.clear_with(200)
    pixmap.save(path)
    return path


def _draw_black_region(path: Path, *, box: tuple[int, int, int, int]) -> None:
    with Image.open(path) as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle(box, fill="black")
        image.save(path)


def _write_quality_sidecar(path: Path, *, warning_kind: str) -> None:
    (path.with_suffix(f"{path.suffix}.json")).write_text(
        json.dumps(
            {
                "path": str(path),
                "quality": {
                    "ok": True,
                    "metrics": {"width": 64, "height": 48},
                    "warnings": [
                        {
                            "kind": warning_kind,
                            "severity": "warning",
                            "message": "Synthetic quality warning for contract testing.",
                            "details": {"source": "test"},
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


def test_mcp_tool_registry_contains_initial_contract() -> None:
    assert {
        "compile_rendered_beamer",
        "create_run",
        "extract_source_pages",
        "ingest_source",
        "list_model_providers",
        "list_theme_presets",
        "list_visual_artifacts",
        "plan_deck",
        "render_beamer",
        "render_layout_placeholders",
        "render_rich_beamer",
        "render_slide_preview",
        "render_source_preview",
        "render_zoom_crop",
        "validate_layout_overflow",
        "validate_run",
    } == MCP_TOOL_NAMES


def test_mcp_resource_registry_contains_rich_visual_deck_guidance() -> None:
    assert {
        "academic-slides://layouts/rich_slide_patterns",
        "academic-slides://prompts/draft_academic_deck",
        "academic-slides://prompts/draft_visual_academic_deck",
        "academic-slides://prompts/didactic_quality_rubric",
        "academic-slides://prompts/review_slide_validation",
        "academic-slides://prompts/review_visual_artifacts",
        "academic-slides://prompts/visual_quality_rubric",
        "academic-slides://schemas/rich_slide_plan",
        "academic-slides://themes/default_visual_academic",
        "academic-slides://themes/unb_visual_academic",
    } == MCP_RESOURCE_URIS


def test_build_app_returns_arcade_app_with_expected_name() -> None:
    app = build_app()

    assert app.name == "academic_slides_harness"


def test_create_run_returns_structured_content(tmp_path: Path) -> None:
    result = create_run(base_dir=tmp_path, title="Compact Operators")

    assert result.ok is True
    assert Path(result.structured_content["run_dir"]).exists()
    assert Path(result.structured_content["manifest_path"]).exists()
    assert result.structured_content["state"] == "created"


def test_create_run_rejects_title_without_usable_slug(tmp_path: Path) -> None:
    result = create_run(base_dir=tmp_path, title=" !!! ")

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_title"
    assert not (tmp_path / "manifest.json").exists()


def test_create_run_rejects_base_dir_that_is_file(tmp_path: Path) -> None:
    base_file = tmp_path / "not-a-directory"
    base_file.write_text("file", encoding="utf-8")

    result = create_run(base_dir=str(base_file), title="Bad Base")

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_base_dir"


def test_build_app_exposes_every_registered_tool_over_stdio_contract() -> None:
    app = build_app()
    tool_names = {
        f"{tool_name.toolkit_name}_{tool_name.name}" for tool_name in app._catalog.get_tool_names()
    }

    expected = {
        "AcademicSlidesHarness_CompileRenderedBeamer",
        "AcademicSlidesHarness_CreateRun",
        "AcademicSlidesHarness_ExtractSourcePages",
        "AcademicSlidesHarness_IngestSource",
        "AcademicSlidesHarness_ListModelProviders",
        "AcademicSlidesHarness_ListThemePresets",
        "AcademicSlidesHarness_ListVisualArtifacts",
        "AcademicSlidesHarness_PlanDeck",
        "AcademicSlidesHarness_RenderBeamer",
        "AcademicSlidesHarness_RenderLayoutPlaceholders",
        "AcademicSlidesHarness_RenderRichBeamer",
        "AcademicSlidesHarness_RenderSlidePreview",
        "AcademicSlidesHarness_RenderSourcePreview",
        "AcademicSlidesHarness_RenderZoomCrop",
        "AcademicSlidesHarness_ValidateLayoutOverflow",
        "AcademicSlidesHarness_ValidateRun",
    }
    assert tool_names == expected


def test_build_app_registers_rich_visual_guidance_resources() -> None:
    app = build_app()

    resource_uris = {resource.uri for resource, _handler in app._initial_resources}

    assert resource_uris == MCP_RESOURCE_URIS


def test_render_layout_placeholders_creates_visual_pngs_with_metadata(tmp_path: Path) -> None:
    result = render_layout_placeholders(
        output_dir=str(tmp_path / "layouts"),
        layouts="hero_visual,figure_explanation",
    )

    assert result.ok is True
    assert result.structured_content["layouts"] == ["hero_visual", "figure_explanation"]
    artifacts = result.structured_content["artifacts"]
    assert len(artifacts) == 2
    for artifact in artifacts:
        path = Path(artifact["path"])
        assert path.is_file()
        assert artifact["format"] == "png"
        assert artifact["width"] == 1280
        assert artifact["height"] == 720
        assert artifact["sha256"]
        assert artifact["layout"] in {"hero_visual", "figure_explanation"}
        assert artifact["required_blocks"]


def test_render_layout_placeholders_supports_native_math_and_table_layouts(
    tmp_path: Path,
) -> None:
    result = render_layout_placeholders(
        output_dir=str(tmp_path / "layouts"),
        layouts="equation_explanation,table_explanation",
    )

    assert result.ok is True
    assert result.structured_content["layouts"] == [
        "equation_explanation",
        "table_explanation",
    ]
    assert {artifact["layout"] for artifact in result.structured_content["artifacts"]} == {
        "equation_explanation",
        "table_explanation",
    }


def test_render_layout_placeholders_supports_varied_academic_templates(
    tmp_path: Path,
) -> None:
    result = render_layout_placeholders(
        output_dir=str(tmp_path / "layouts"),
        layouts=(
            "correction_pipeline,derivation_steps,concept_matrix,"
            "two_equation_comparison,mode_plot,checklist_summary"
        ),
    )

    assert result.ok is True
    assert result.structured_content["layouts"] == [
        "correction_pipeline",
        "derivation_steps",
        "concept_matrix",
        "two_equation_comparison",
        "mode_plot",
        "checklist_summary",
    ]


def test_render_layout_placeholders_rejects_existing_artifacts_by_default(
    tmp_path: Path,
) -> None:
    render_layout_placeholders(output_dir=str(tmp_path), layouts="takeaway")

    result = render_layout_placeholders(output_dir=str(tmp_path), layouts="takeaway")

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "artifact_exists"


def test_render_layout_placeholders_returns_typed_error_for_unknown_layout(
    tmp_path: Path,
) -> None:
    result = render_layout_placeholders(output_dir=str(tmp_path), layouts="unknown_layout")

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_layout"


def test_list_theme_presets_returns_default_visual_academic_preset() -> None:
    result = list_theme_presets()

    assert result.ok is True
    presets = result.structured_content["presets"]
    assert len(presets) >= 2
    default = next(preset for preset in presets if preset["name"] == "default_visual_academic")
    assert default["resource_uri"] == "academic-slides://themes/default_visual_academic"
    assert default["sha256"]
    assert default["colors"]["primary"] == "#1F4E79"
    assert default["logo"]["path"] is None
    unb = next(preset for preset in presets if preset["name"] == "unb_visual_academic")
    assert unb["resource_uri"] == "academic-slides://themes/unb_visual_academic"
    assert unb["colors"]["primary"] == "#003366"
    assert unb["colors"]["accent"] == "#006633"


def test_list_model_providers_returns_redacted_structured_content(monkeypatch) -> None:
    fake_key = "sk-proj-" + ("x" * 48)
    monkeypatch.setenv("OPENAI_API_KEY", fake_key)
    monkeypatch.setattr(
        "academic_slides_harness.llm.providers.OllamaProvider.is_available",
        lambda _self: False,
    )
    monkeypatch.setattr(
        "academic_slides_harness.llm.providers.OllamaProvider.list_models",
        lambda _self: [],
    )

    result = list_model_providers()
    raw_result = json.dumps(result.structured_content)

    assert result.ok is True
    assert result.structured_content["providers"]["openai"]["api_key_configured"] is True
    assert fake_key not in raw_result


def test_list_theme_presets_returns_typed_error_when_default_preset_is_invalid(
    monkeypatch,
) -> None:
    def raise_missing_preset(name_or_path: object) -> dict[str, object]:
        raise ThemePresetError(
            "missing_preset",
            "missing default preset",
            details={"name": str(name_or_path)},
        )

    monkeypatch.setattr(
        "academic_slides_harness.mcp.server.load_theme_preset",
        raise_missing_preset,
    )

    result = list_theme_presets()

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_preset"


def test_build_app_theme_resource_does_not_crash_when_preset_is_invalid(
    monkeypatch,
) -> None:
    def raise_missing_preset(name_or_path: object) -> dict[str, object]:
        raise ThemePresetError(
            "missing_preset",
            "missing default preset",
            details={"name": str(name_or_path)},
        )

    monkeypatch.setattr(
        "academic_slides_harness.mcp.server.load_theme_preset",
        raise_missing_preset,
    )

    app = build_app()
    resources = {str(resource.uri): handler for resource, handler in app._initial_resources}

    assert "academic-slides://themes/default_visual_academic" in resources
    assert "academic-slides://themes/unb_visual_academic" in resources


def test_compile_rendered_beamer_returns_typed_timeout_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tex_path = tmp_path / "deck.tex"
    tex_path.write_text("\\documentclass{beamer}", encoding="utf-8")

    def fail_timeout(*args: object, **kwargs: object) -> Path:
        raise TimeoutError("Tectonic timed out after 1 seconds")

    monkeypatch.setattr(
        "academic_slides_harness.mcp.server.compile_tex_with_tectonic",
        fail_timeout,
    )

    result = compile_rendered_beamer(tex_path=str(tex_path), output_dir=str(tmp_path / "build"))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "compile_timeout"


def test_ingest_source_returns_typed_error_for_missing_pdf(tmp_path: Path) -> None:
    result = ingest_source(source_path=str(tmp_path / "missing.pdf"))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_input"


def test_ingest_source_returns_typed_error_for_invalid_pdf(tmp_path: Path) -> None:
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("not a pdf", encoding="utf-8")

    result = ingest_source(source_path=str(invalid_pdf))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "ingest_failed"


def test_ingest_source_returns_typed_error_for_directory(tmp_path: Path) -> None:
    result = ingest_source(source_path=str(tmp_path))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_input"


def test_extract_source_pages_returns_page_text_for_mcp_planning(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")

    result = extract_source_pages(source_pdf=str(source), pages="1", max_chars_per_page=50)

    assert result.ok is True
    assert result.structured_content["source_pdf"] == str(source.resolve())
    assert result.structured_content["page_count"] == 1
    pages = result.structured_content["pages"]
    assert pages == [
        {
            "page": 1,
            "text": "Academic Slides Harness",
            "char_count": len("Academic Slides Harness"),
            "truncated": False,
        }
    ]


def test_extracted_source_page_text_is_safe_for_mcp_json_transport() -> None:
    surrogate = chr(0xDCC3)

    text = normalize_extracted_pdf_text(f"Alpha{surrogate}  Beta\nGamma")

    assert text == "Alpha Beta Gamma"
    assert all(not 0xD800 <= ord(char) <= 0xDFFF for char in text)


def test_extract_source_pages_returns_typed_error_for_missing_pdf(tmp_path: Path) -> None:
    result = extract_source_pages(source_pdf=str(tmp_path / "missing.pdf"), pages="1")

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_input"


def test_extract_source_pages_returns_typed_error_for_invalid_page_selection(
    tmp_path: Path,
) -> None:
    result = extract_source_pages(source_pdf=str(tmp_path / "missing.pdf"), pages="0")

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_page_selection"


def test_render_beamer_returns_tex_hash(tmp_path: Path) -> None:
    result = render_beamer(
        output_dir=str(tmp_path),
        title="Hashable Deck",
        slides=[{"title": "One", "bullets": ["A"]}],
    )

    assert result.ok is True
    assert Path(result.structured_content["deck_tex"]).exists()
    assert result.structured_content["sha256"]


def test_render_beamer_accepts_plan_deck_slide_shape(tmp_path: Path) -> None:
    plan = plan_deck(
        title="Chainable Deck",
        excerpts=["First deterministic finding. Second reproducible finding. Third implication."],
        max_slides=1,
    )

    result = render_beamer(
        output_dir=str(tmp_path),
        title=plan.structured_content["title"],
        slides=plan.structured_content["slides"],
    )

    tex = Path(result.structured_content["deck_tex"]).read_text(encoding="utf-8")
    assert result.ok is True
    assert "\\begin{frame}{Chainable Deck: 1}" in tex
    assert "\\item First deterministic finding" in tex


def test_render_beamer_returns_typed_error_for_bad_slide_shape(tmp_path: Path) -> None:
    result = render_beamer(
        output_dir=str(tmp_path),
        title="Bad Deck",
        slides=[{"title": "Missing bullets"}],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_slide"


def test_render_beamer_returns_typed_error_when_slides_is_not_list(tmp_path: Path) -> None:
    result = render_beamer(
        output_dir=str(tmp_path),
        title="Bad Deck",
        slides="not a list",
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_slides"


def test_render_rich_beamer_embeds_visual_artifact_without_itemize(tmp_path: Path) -> None:
    visual_path = _make_png(tmp_path / "source.png", width=24, height=16)

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Evidence First",
                "layout": "figure_explanation",
                "learning_goal": "Tie the image to the measurement claim.",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "The visual artifact is the evidence."},
                    {"type": "source_citation", "source_page": 2},
                ],
            }
        ],
    )

    tex = Path(result.structured_content["deck_tex"]).read_text(encoding="utf-8")
    assert result.ok is True
    assert "\\includegraphics" in tex
    assert "\\begin{itemize}" not in tex
    assert result.structured_content["slide_count"] == 1
    assert result.structured_content["assets"][0]["source_path"] == str(visual_path.resolve())
    assert Path(result.structured_content["assets"][0]["deck_path"]).is_file()
    assert result.structured_content["assets"][0]["width"] == 24
    assert result.structured_content["assets"][0]["height"] == 16
    assert result.structured_content["assets"][0]["format"] == "PNG"
    assert result.structured_content["assets"][0]["converted"] is False
    assert "assets/" in tex


def test_render_rich_beamer_rejects_page_snapshot_as_hero_visual(tmp_path: Path) -> None:
    visual_path = _make_png(tmp_path / "source_pdf-p1-144dpi.png")
    _write_quality_sidecar(visual_path, warning_kind="page_like_snapshot")

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Whole Page Is Not Evidence",
                "layout": "hero_visual",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "A page screenshot should not be a hero visual."},
                    {"type": "source_citation", "source_page": 1},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "visual_quality_failed"
    assert error["details"]["slide_index"] == 1
    assert error["details"]["block_index"] == 1
    assert error["details"]["layout"] == "hero_visual"
    assert error["details"]["artifact_path"] == str(visual_path.resolve())
    assert error["details"]["warning_kinds"] == ["page_like_snapshot"]
    assert not (tmp_path / "rendered" / "assets").exists()
    assert not (tmp_path / "rendered" / "deck.tex").exists()


def test_render_rich_beamer_rejects_text_heavy_visual_crop(tmp_path: Path) -> None:
    visual_path = _make_png(tmp_path / "source_pdf-p4-crop-144dpi-z2.5.png")
    _write_quality_sidecar(visual_path, warning_kind="text_heavy_crop")

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Text Heavy Crop",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "The image must be figure evidence, not body text."},
                    {"type": "source_citation", "source_page": 4},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "visual_quality_failed"
    assert error["details"]["slide_index"] == 1
    assert error["details"]["block_index"] == 1
    assert error["details"]["layout"] == "figure_explanation"
    assert error["details"]["warning_kinds"] == ["text_heavy_crop"]
    assert "crop tighter" in error["details"]["remediation"]
    assert not (tmp_path / "rendered" / "assets").exists()


def test_render_rich_beamer_allows_visual_quality_override_with_metadata(
    tmp_path: Path,
) -> None:
    visual_path = _make_png(tmp_path / "source_pdf-p4-crop-144dpi-z2.5.png")
    _write_quality_sidecar(visual_path, warning_kind="text_heavy_crop")

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Explicit Override",
                "layout": "figure_explanation",
                "blocks": [
                    {
                        "type": "visual",
                        "artifact_path": str(visual_path),
                        "allow_visual_quality_warnings": True,
                    },
                    {"type": "claim", "text": "This warning is intentionally accepted."},
                    {"type": "source_citation", "source_page": 4},
                ],
            }
        ],
    )

    assert result.ok is True
    asset = result.structured_content["assets"][0]
    assert asset["quality_override"] is True
    assert asset["quality"]["warnings"][0]["kind"] == "text_heavy_crop"
    assert Path(asset["deck_path"]).is_file()


def test_render_rich_beamer_returns_typed_error_for_missing_visual(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Missing Evidence",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "visual", "artifact_path": str(tmp_path / "missing.png")},
                    {"type": "claim", "text": "This should not render."},
                ],
            }
        ],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_visual_artifact"


def test_validate_layout_overflow_returns_typed_failure_with_region_crop(
    tmp_path: Path,
) -> None:
    visual_path = _make_png(tmp_path / "deck_pdf-p1-144dpi.png", width=1000, height=600)
    _draw_black_region(visual_path, box=(660, 240, 820, 270))

    result = validate_layout_overflow(
        screenshots_dir=str(tmp_path),
        output_dir=str(tmp_path / "overflow"),
        slides="1",
        protected_regions=[
            {
                "label": "right rail guard",
                "x": 0.64,
                "y": 0.18,
                "width": 0.10,
                "height": 0.60,
                "max_ink_ratio": 0.01,
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "layout_overflow_detected"
    warning = error["details"]["warnings"][0]
    assert warning["kind"] == "protected_region_ink"
    assert Path(warning["details"]["crop_path"]).is_file()


def test_validate_layout_overflow_passes_clean_slide_preview(tmp_path: Path) -> None:
    visual_path = _make_png(tmp_path / "deck_pdf-p1-144dpi.png", width=1000, height=600)
    _draw_black_region(visual_path, box=(80, 120, 420, 300))

    result = validate_layout_overflow(
        screenshots_dir=str(tmp_path),
        output_dir=str(tmp_path / "overflow"),
        slides="1",
        protected_regions=[
            {
                "label": "right rail guard",
                "x": 0.64,
                "y": 0.18,
                "width": 0.10,
                "height": 0.60,
                "max_ink_ratio": 0.01,
            }
        ],
    )

    assert result.ok is True
    assert result.structured_content["ok"] is True
    assert result.structured_content["warnings"] == []


def test_render_rich_beamer_accepts_native_equation_layout_without_visual(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Native Equation Deck",
        slides=[
            {
                "title": "A equacao deve ser texto vetorial nativo",
                "layout": "equation_explanation",
                "learning_goal": "Ler a aceleracao especifica sem depender de crop.",
                "blocks": [
                    {
                        "type": "latex_equation",
                        "latex": r"f^b = R_n^b (a^n - g^n)",
                        "caption": "Equacao nativa em LaTeX, nao imagem.",
                    },
                    {"type": "claim", "text": "A formula permanece editavel no Beamer."},
                    {"type": "source_citation", "source_page": 3},
                ],
            }
        ],
    )

    tex = Path(result.structured_content["deck_tex"]).read_text(encoding="utf-8")
    assert result.ok is True
    assert result.structured_content["layouts"] == ["equation_explanation"]
    assert result.structured_content["assets"] == []
    assert r"f^b = R_n^b (a^n - g^n)" in tex
    assert "\\includegraphics" not in tex


def test_render_rich_beamer_accepts_native_table_layout_without_visual(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Native Table Deck",
        slides=[
            {
                "title": "Tabela comparativa nativa",
                "layout": "table_explanation",
                "blocks": [
                    {
                        "type": "latex_table",
                        "caption": "Resumo compacto em tabela editavel.",
                        "headers": ["Grandeza", "Unidade"],
                        "rows": [["aceleracao", "m/s^2"], ["gravidade", "m/s^2"]],
                    },
                    {"type": "claim", "text": "A tabela deve ser gerada como tabular."},
                    {"type": "source_citation", "source_page": 4},
                ],
            }
        ],
    )

    tex = Path(result.structured_content["deck_tex"]).read_text(encoding="utf-8")
    assert result.ok is True
    assert "\\begin{tabular}" in tex
    assert "Grandeza" in tex
    assert "aceleracao" in tex
    assert "\\includegraphics" not in tex


def test_render_rich_beamer_rejects_unsafe_native_latex_equation(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Unsafe Equation Deck",
        slides=[
            {
                "title": "Unsafe Equation",
                "layout": "equation_explanation",
                "blocks": [
                    {
                        "type": "latex_equation",
                        "latex": r"\input{secret}",
                    },
                    {"type": "source_citation", "source_page": 1},
                ],
            }
        ],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_latex_equation"
    assert not (tmp_path / "rendered" / "deck.tex").exists()


def test_render_rich_beamer_rejects_unsafe_native_latex_table_cell(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Unsafe Table Deck",
        slides=[
            {
                "title": "Unsafe Table",
                "layout": "table_explanation",
                "blocks": [
                    {
                        "type": "latex_table",
                        "headers": ["Termo", "Papel"],
                        "rows": [[r"\input{secret}", "bad"]],
                    },
                    {"type": "source_citation", "source_page": 1},
                ],
            }
        ],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_latex_table"
    assert not (tmp_path / "rendered" / "deck.tex").exists()


def test_render_rich_beamer_returns_typed_error_for_corrupt_visual(
    tmp_path: Path,
) -> None:
    visual_path = tmp_path / "broken.png"
    visual_path.write_text("not an image", encoding="utf-8")

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Broken Evidence",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "This should not render."},
                ],
            }
        ],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_visual_artifact"
    assert not (tmp_path / "rendered" / "assets").exists()


def test_render_rich_beamer_returns_typed_error_for_tiny_visual(
    tmp_path: Path,
) -> None:
    visual_path = tmp_path / "tiny.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 8, 8), False)
    pixmap.clear_with(200)
    pixmap.save(visual_path)

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Tiny Evidence",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "This should not render."},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "image_too_small"
    assert error["details"]["width"] == 8
    assert error["details"]["height"] == 8
    assert not (tmp_path / "rendered" / "assets").exists()


def test_render_rich_beamer_requires_visual_block_for_figure_layout(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "No Visual Block",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "claim", "text": "This layout requires a visual block."},
                    {"type": "source_citation", "source_page": 2},
                ],
            }
        ],
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_slide"


def test_render_rich_beamer_rejects_title_overflow_before_rendering(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "A" * 65,
                "layout": "takeaway",
                "blocks": [
                    {"type": "claim", "text": "Short claim."},
                    {"type": "source_citation", "source_page": 2},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "text_overflow_risk"
    assert error["details"]["field"] == "title"
    assert error["details"]["max_chars"] == 64
    assert not (tmp_path / "rendered" / "deck.tex").exists()


def test_render_rich_beamer_rejects_claim_overflow_before_copying_visual(
    tmp_path: Path,
) -> None:
    visual_path = tmp_path / "source.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 24, 16), False)
    pixmap.clear_with(200)
    pixmap.save(visual_path)

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Evidence First",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "A" * 121},
                    {"type": "source_citation", "source_page": 2},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "text_overflow_risk"
    assert error["details"]["block_type"] == "claim"
    assert error["details"]["max_chars"] == 120
    assert not (tmp_path / "rendered" / "assets").exists()


def test_render_rich_beamer_rejects_explanation_overflow(
    tmp_path: Path,
) -> None:
    visual_path = tmp_path / "source.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 24, 16), False)
    pixmap.clear_with(200)
    pixmap.save(visual_path)

    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Evidence First",
                "layout": "figure_explanation",
                "blocks": [
                    {"type": "visual", "artifact_path": str(visual_path)},
                    {"type": "claim", "text": "Short claim."},
                    {"type": "explanation", "text": "A" * 221},
                    {"type": "source_citation", "source_page": 2},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "text_overflow_risk"
    assert error["details"]["block_type"] == "explanation"
    assert error["details"]["max_chars"] == 220


def test_render_rich_beamer_rejects_too_many_workflow_steps(
    tmp_path: Path,
) -> None:
    result = render_rich_beamer(
        output_dir=str(tmp_path / "rendered"),
        title="Visual Deck",
        slides=[
            {
                "title": "Workflow",
                "layout": "workflow_steps",
                "blocks": [
                    {
                        "type": "steps",
                        "items": [
                            "Normalize channels",
                            "Segment structures",
                            "Measure intensities",
                            "Review artifacts",
                            "Export table",
                            "Archive raw images",
                        ],
                    },
                    {"type": "source_citation", "source_page": 2},
                ],
            }
        ],
    )

    assert result.ok is False
    error = result.structured_content["error"]
    assert error["kind"] == "text_overflow_risk"
    assert error["details"]["field"] == "steps"
    assert error["details"]["max_items"] == 5


def test_render_beamer_strips_numbered_body_markers(tmp_path: Path) -> None:
    result = render_beamer(
        output_dir=str(tmp_path),
        title="Numbered Deck",
        slides=[{"title": "One", "body": "1. First\n2. Second"}],
    )

    tex = Path(result.structured_content["deck_tex"]).read_text(encoding="utf-8")
    assert "\\item First" in tex
    assert "\\item 1. First" not in tex


def test_validate_run_returns_typed_error_for_missing_manifest(tmp_path: Path) -> None:
    run_dir = tmp_path / "incomplete-run"
    (run_dir / "screenshots").mkdir(parents=True)

    result = validate_run(run_dir=str(run_dir))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "validation_failed"
    details = result.structured_content["error"]["details"]
    assert details["ok"] is False
    assert details["checks"] == {
        "run_dir_exists": True,
        "screenshots_dir_exists": True,
        "manifest_exists": False,
    }


def test_validate_run_rejects_unreadable_manifest_json(tmp_path: Path) -> None:
    created = create_run(base_dir=tmp_path, title="Broken Manifest")
    run_dir = Path(created.structured_content["run_dir"])
    manifest_path = Path(created.structured_content["manifest_path"])
    manifest_path.write_text("{not-json", encoding="utf-8")

    result = validate_run(run_dir=str(run_dir))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "validation_failed"
    checks = result.structured_content["error"]["details"]["checks"]
    assert checks["manifest_exists"] is True
    assert checks["manifest_parseable"] is False
    assert checks["manifest_schema_valid"] is False


def test_validate_run_rejects_manifest_schema_errors(tmp_path: Path) -> None:
    created = create_run(base_dir=tmp_path, title="Bad Manifest Schema")
    run_dir = Path(created.structured_content["run_dir"])
    manifest_path = Path(created.structured_content["manifest_path"])
    manifest_path.write_text(json.dumps({"run_id": "missing-required-fields"}), encoding="utf-8")

    result = validate_run(run_dir=str(run_dir))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "validation_failed"
    checks = result.structured_content["error"]["details"]["checks"]
    assert checks["manifest_parseable"] is True
    assert checks["manifest_schema_valid"] is False


def test_list_visual_artifacts_returns_dimensions_and_hash(tmp_path: Path) -> None:
    image_path = tmp_path / "artifact.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 8), False)
    pixmap.clear_with(255)
    pixmap.save(image_path)

    result = list_visual_artifacts(screenshots_dir=str(tmp_path))

    artifact = result.structured_content["artifacts"][0]
    assert artifact["path"] == str(image_path.resolve())
    assert artifact["width"] == 12
    assert artifact["height"] == 8
    assert artifact["sha256"]


def test_list_visual_artifacts_restores_harness_metadata_from_filename(tmp_path: Path) -> None:
    image_path = tmp_path / "deck_pdf-p2-crop-144dpi-z2.png"
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 10), False)
    pixmap.clear_with(255)
    pixmap.save(image_path)

    result = list_visual_artifacts(screenshots_dir=str(tmp_path))

    artifact = result.structured_content["artifacts"][0]
    assert artifact["target"] == "deck_pdf"
    assert artifact["page"] == 2
    assert artifact["dpi"] == 144
    assert artifact["scale"] == 2.0
    assert artifact["zoom"] == 2.0


def test_list_visual_artifacts_returns_typed_error_for_missing_dir(tmp_path: Path) -> None:
    result = list_visual_artifacts(screenshots_dir=str(tmp_path / "missing"))

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_input"


def test_render_zoom_crop_returns_typed_error_for_invalid_target(tmp_path: Path) -> None:
    result = render_zoom_crop(
        pdf_path=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        target="bad_target",
        page=1,
        crop={"x": 0, "y": 0, "width": 1, "height": 1},
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_target"


def test_render_zoom_crop_returns_typed_error_for_invalid_page(tmp_path: Path) -> None:
    result = render_zoom_crop(
        pdf_path=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        target="deck_pdf",
        page=0,
        crop={"x": 0, "y": 0, "width": 1, "height": 1},
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_page_selection"


def test_render_zoom_crop_returns_typed_error_for_invalid_crop_shape(tmp_path: Path) -> None:
    missing_width = render_zoom_crop(
        pdf_path=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        target="deck_pdf",
        page=1,
        crop={"x": 0, "y": 0, "height": 1},
    )
    non_positive_height = render_zoom_crop(
        pdf_path=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        target="deck_pdf",
        page=1,
        crop={"x": 0, "y": 0, "width": 1, "height": 0},
    )

    assert missing_width.ok is False
    assert missing_width.structured_content["error"]["kind"] == "invalid_crop"
    assert non_positive_height.ok is False
    assert non_positive_height.structured_content["error"]["kind"] == "invalid_crop"


def test_render_slide_preview_returns_typed_error_for_invalid_page_selection(
    tmp_path: Path,
) -> None:
    result = render_slide_preview(
        deck_pdf=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        slides="0",
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_page_selection"


def test_render_source_preview_returns_typed_error_for_invalid_page_selection(
    tmp_path: Path,
) -> None:
    result = render_source_preview(
        source_pdf=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        pages="0",
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_page_selection"


def test_render_slide_preview_returns_typed_error_for_invalid_render_options(
    tmp_path: Path,
) -> None:
    result = render_slide_preview(
        deck_pdf=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        slides="1",
        resolution="bad",
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "invalid_render_options"


def test_render_source_preview_returns_typed_error_for_missing_pdf(tmp_path: Path) -> None:
    result = render_source_preview(
        source_pdf=str(tmp_path / "missing.pdf"),
        output_dir=str(tmp_path),
        pages="1",
    )

    assert result.ok is False
    assert result.structured_content["error"]["kind"] == "missing_input"


def test_render_source_preview_returns_typed_error_for_existing_artifact(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")
    output_dir = tmp_path / "screens"
    first = render_source_preview(
        source_pdf=str(source),
        output_dir=str(output_dir),
        pages="1",
        resolution="fast",
    )

    second = render_source_preview(
        source_pdf=str(source),
        output_dir=str(output_dir),
        pages="1",
        resolution="fast",
    )

    assert first.ok is True
    assert second.ok is False
    assert second.structured_content["error"]["kind"] == "artifact_exists"


def test_render_source_preview_allows_explicit_overwrite(tmp_path: Path) -> None:
    source = _make_pdf(tmp_path / "source.pdf")
    output_dir = tmp_path / "screens"
    render_source_preview(
        source_pdf=str(source),
        output_dir=str(output_dir),
        pages="1",
        resolution="fast",
    )

    result = render_source_preview(
        source_pdf=str(source),
        output_dir=str(output_dir),
        pages="1",
        resolution="fast",
        overwrite=True,
    )

    assert result.ok is True
    assert result.structured_content["artifacts"][0]["path"].endswith("source_pdf-p1-72dpi.png")
