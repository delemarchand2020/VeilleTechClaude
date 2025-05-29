"""
Configuration globale pour pytest.

Ce fichier contient les fixtures communes et la configuration
partagée entre tous les tests du projet.
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from pathlib import Path

# Configuration des variables d'environnement pour les tests
os.environ['TESTING'] = 'true'
os.environ['LOG_LEVEL'] = 'INFO'


@pytest.fixture(scope="session")
def event_loop():
    """Fixture pour gérer l'event loop asyncio pour toute la session de test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Fixture fournissant um répertoire temporaire pour les tests."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def sample_datetime():
    """Fixture fournissant une date/heure standard pour les tests."""
    return datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_http_session():
    """Fixture fournissant une session HTTP mockée pour les tests."""
    session = Mock()
    session.get = Mock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_successful_response():
    """Fixture fournissant une réponse HTTP réussie mockée."""
    response = Mock()
    response.status = 200
    response.status_code = 200
    response.headers = {'content-type': 'application/rss+xml'}
    response.text = AsyncMock(return_value="<xml>success</xml>")
    return response


@pytest.fixture
def mock_failed_response():
    """Fixture fournissant une réponse HTTP d'échec mockée."""
    response = Mock()
    response.status = 404
    response.status_code = 404
    response.headers = {}
    return response


@pytest.fixture
def sample_rss_xml():
    """Fixture fournissant un contenu RSS XML d'exemple."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test RSS Feed</title>
            <description>A test RSS feed for unit tests</description>
            <link>https://example.com</link>
            <item>
                <title>Test Article 1</title>
                <link>https://example.com/article1</link>
                <description>Description of test article 1</description>
                <author>Test Author 1</author>
                <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
                <guid>test-article-1</guid>
                <category>Test</category>
                <category>Example</category>
            </item>
            <item>
                <title>Test Article 2</title>
                <link>https://example.com/article2</link>
                <description>Description of test article 2</description>
                <author>Test Author 2</author>
                <pubDate>Sun, 14 Jan 2024 10:30:00 GMT</pubDate>
                <guid>test-article-2</guid>
                <category>Test</category>
            </item>
        </channel>
    </rss>'''


@pytest.fixture
def test_keywords():
    """Fixture fournissant des mots-clés standards pour les tests."""
    return ["AI", "Machine Learning", "Python", "Technology"]


@pytest.fixture(autouse=True)
def cleanup_env():
    """Fixture qui s'exécute automatiquement pour nettoyer l'environnement après chaque test."""
    yield
    # Nettoyage après le test si nécessaire
    pass


# Configuration des markers
def pytest_configure(config):
    """Configuration personnalisée de pytest."""
    config.addinivalue_line(
        "markers", "unit: marque un test comme test unitaire"
    )
    config.addinivalue_line(
        "markers", "integration: marque un test comme test d'intégration"
    )
    config.addinivalue_line(
        "markers", "connector: test spécifique aux connecteurs"
    )
    config.addinivalue_line(
        "markers", "slow: test lent qui peut être skippé"
    )
    config.addinivalue_line(
        "markers", "external: test nécessitant des ressources externes"
    )


def pytest_collection_modifyitems(config, items):
    """Modifie la collecte des tests pour ajouter des markers automatiquement."""
    for item in items:
        # Ajouter le marker 'unit' par défaut si aucun autre marker n'est présent
        if not any(marker.name in ['integration', 'slow', 'external'] 
                  for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
        
        # Ajouter le marker 'connector' aux tests des connecteurs
        if 'connector' in str(item.fspath):
            item.add_marker(pytest.mark.connector)


def pytest_runtest_setup(item):
    """Configuration avant l'exécution de chaque test."""
    # Skip les tests externes si pas en mode CI ou si demandé
    if 'external' in [marker.name for marker in item.iter_markers()]:
        if not os.environ.get('RUN_EXTERNAL_TESTS'):
            pytest.skip("Test externe skippé (définir RUN_EXTERNAL_TESTS pour l'exécuter)")


# Hooks pour le reporting
def pytest_report_header(config):
    """Ajoute des informations dans l'en-tête du rapport de test."""
    return [
        f"Projet: Agent de Veille Intelligente",
        f"Python path: {os.environ.get('PYTHONPATH', 'Non défini')}",
        f"Mode test: {os.environ.get('TESTING', 'false')}",
    ]
