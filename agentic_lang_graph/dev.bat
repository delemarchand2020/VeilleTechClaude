@echo off
REM Script batch pour faciliter l'utilisation des tests et du développement
REM Usage: dev.bat [commande]

if "%1"=="" goto :help
if "%1"=="help" goto :help
if "%1"=="install" goto :install
if "%1"=="test" goto :test
if "%1"=="test-unit" goto :test-unit
if "%1"=="test-integration" goto :test-integration
if "%1"=="test-connector" goto :test-connector
if "%1"=="test-coverage" goto :test-coverage
if "%1"=="test-fast" goto :test-fast
if "%1"=="clean" goto :clean
if "%1"=="run" goto :run
goto :help

:help
echo.
echo Scripts de développement pour Agent de Veille Intelligente
echo.
echo Commandes disponibles:
echo   install        - Installer les dépendances
echo   test           - Exécuter tous les tests
echo   test-unit      - Exécuter les tests unitaires seulement
echo   test-integration - Exécuter les tests d'intégration seulement
echo   test-connector - Exécuter les tests des connecteurs seulement
echo   test-coverage  - Exécuter les tests avec couverture de code
echo   test-fast      - Exécuter les tests rapides seulement
echo   clean          - Nettoyer les fichiers temporaires
echo   run            - Exécuter l'application principale
echo   help           - Afficher cette aide
echo.
goto :end

:install
echo Installation des dépendances...
pip install -r requirements.txt
echo Dépendances installées avec succès!
goto :end

:test
echo Exécution de tous les tests...
python run_tests.py
goto :end

:test-unit
echo Exécution des tests unitaires...
python run_tests.py --unit
goto :end

:test-integration
echo Exécution des tests d'intégration...
python run_tests.py --integration
goto :end

:test-connector
echo Exécution des tests des connecteurs...
python run_tests.py --connector
goto :end

:test-coverage
echo Exécution des tests avec couverture...
python run_tests.py --coverage --html
echo Rapport de couverture généré dans htmlcov/index.html
goto :end

:test-fast
echo Exécution des tests rapides...
python run_tests.py --fast
goto :end

:clean
echo Nettoyage des fichiers temporaires...
if exist __pycache__ rmdir /s /q __pycache__
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist htmlcov rmdir /s /q htmlcov
if exist .coverage del .coverage
if exist coverage.xml del coverage.xml
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
for /r . %%f in (*.pyc) do @if exist "%%f" del "%%f"
echo Nettoyage terminé!
goto :end

:run
echo Exécution de l'application principale...
python main.py
goto :end

:end
