"""Tests unitaires pour le module PromptLoader."""

from pathlib import Path

import pytest

from agentic_lang_graph.src.utils.prompt_loader import PromptLoader


def _create_prompt(tmp_path: Path, relative_path: str, content: str) -> Path:
    """Crée un fichier de prompt dans l'arborescence temporaire."""

    file_path = tmp_path / Path(relative_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_load_prompt_cache_and_reload(tmp_path: Path) -> None:
    """Le chargement met en cache le contenu et le rechargement reflète les modifications."""

    system_path = _create_prompt(tmp_path, "analyzer/system.md", "Version initiale")

    loader = PromptLoader(prompts_dir=str(tmp_path))

    first_load = loader.load_prompt("analyzer/system")
    assert first_load == "Version initiale"

    cache_key = str(system_path)
    assert cache_key in loader.cache

    system_path.write_text("Nouvelle version", encoding="utf-8")

    cached_load = loader.load_prompt("analyzer/system")
    assert cached_load == "Version initiale"

    loader.reload_prompt("analyzer/system.md")

    reloaded = loader.load_prompt("analyzer/system")
    assert reloaded == "Nouvelle version"


def test_load_prompt_templating(tmp_path: Path) -> None:
    """Le templating remplace les variables et signale les manquantes."""

    _create_prompt(tmp_path, "analyzer/system.md", "Système basique")
    _create_prompt(
        tmp_path,
        "analyzer/templated.md",
        "Bonjour {name}, bienvenue à {place}!",
    )

    loader = PromptLoader(prompts_dir=str(tmp_path))

    formatted = loader.load_prompt(
        "analyzer/templated",
        variables={"name": "Alice", "place": "Wonderland"},
    )
    assert formatted == "Bonjour Alice, bienvenue à Wonderland!"

    with pytest.raises(ValueError):
        loader.load_prompt("analyzer/templated", variables={"name": "Alice"})


def test_list_available_prompts(tmp_path: Path) -> None:
    """La liste des prompts disponibles reflète les fichiers .md présents."""

    _create_prompt(tmp_path, "analyzer/system.md", "System")
    _create_prompt(tmp_path, "analyzer/content_analysis.md", "Content")
    _create_prompt(tmp_path, "synthesizer/executive_summary.md", "Summary")

    loader = PromptLoader(prompts_dir=str(tmp_path))

    available_prompts = loader.list_available_prompts()

    assert set(available_prompts.keys()) == {"analyzer", "synthesizer"}
    assert set(available_prompts["analyzer"]) == {"system", "content_analysis"}
    assert available_prompts["synthesizer"] == ["executive_summary"]
