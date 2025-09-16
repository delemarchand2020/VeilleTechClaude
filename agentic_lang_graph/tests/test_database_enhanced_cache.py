import sqlite3
import sys
from datetime import datetime, timedelta

import agentic_lang_graph.src as ag_src

sys.modules.setdefault("src", ag_src)

from agentic_lang_graph.src.connectors.base_connector import RawContent
from agentic_lang_graph.src.models.analysis_models import ContentAnalysis, DifficultyLevel
from agentic_lang_graph.src.models.database_enhanced import DatabaseManagerEnhanced


def test_analysis_cache_lifecycle(tmp_path):
    """Vérifie le cycle de vie complet d'une entrée de cache d'analyse."""
    db_path = tmp_path / "cache.db"
    manager = DatabaseManagerEnhanced(str(db_path))

    raw_content = RawContent(
        title="LangGraph cache test",
        url="https://example.com/cache",
        source="test",
        content="LangGraph cache validation content."
    )

    analysis = ContentAnalysis(
        relevance_score=8.5,
        difficulty_level=DifficultyLevel.INTERMEDIATE,
        main_topics=["LangGraph", "Caching"],
        key_insights="Cache saves time",
        practical_value=7.0,
        reasons=["Avoid recomputation"],
        recommended=True,
    )

    manager.save_analysis_to_cache(raw_content, analysis, ttl_hours=48)

    first_hit = manager.check_analysis_cache(raw_content, max_age_hours=24)
    assert first_hit.found is True
    assert isinstance(first_hit.analysis, dict)

    with sqlite3.connect(manager.db_path) as conn:
        use_count = conn.execute("SELECT use_count FROM analysis_cache").fetchone()[0]
        assert use_count == 2

    stale_timestamp = (datetime.now() - timedelta(hours=48)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(manager.db_path) as conn:
        conn.execute(
            "UPDATE analysis_cache SET created_date = ?, last_used = ?",
            (stale_timestamp, stale_timestamp),
        )
        conn.commit()

    stale_hit = manager.check_analysis_cache(raw_content, max_age_hours=24)
    assert stale_hit.found is False

    fresh_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(manager.db_path) as conn:
        conn.execute(
            "UPDATE analysis_cache SET created_date = ?, last_used = ?, is_valid = 1",
            (fresh_timestamp, fresh_timestamp),
        )
        conn.commit()

    with sqlite3.connect(manager.db_path) as conn:
        conn.execute(
            "UPDATE analysis_cache SET analysis_result = ?",
            ("{invalid json",),
        )
        conn.commit()

    invalid_hit = manager.check_analysis_cache(raw_content, max_age_hours=24)
    assert invalid_hit.found is False

    with sqlite3.connect(manager.db_path) as conn:
        is_valid = conn.execute("SELECT is_valid FROM analysis_cache").fetchone()[0]
        assert is_valid == 0
