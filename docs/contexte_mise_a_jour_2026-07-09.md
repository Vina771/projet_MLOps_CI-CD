# Contexte mise a jour - 2026-07-09

## Probleme observe

Le pipeline GitLab numero 1 a echoue au stage `test`.

Erreur principale :

```text
ModuleNotFoundError: No module named 'src'
```

Le job `lint` etait passe, mais le job `test` a bloque la suite du pipeline.
Les stages `build`, `scan`, `push` et `deploy` n'ont donc pas ete executes.

## Cause probable

Dans l'image Docker `python:3.11-slim` utilisee par GitLab CI, la racine du
depot n'etait pas toujours disponible dans le chemin d'import Python pendant la
collecte pytest. Le test `tests/test_api.py` ne pouvait donc pas importer
`src.app`.

## Corrections appliquees

- Ajout de `PYTHONPATH: "$CI_PROJECT_DIR"` dans `.gitlab-ci.yml`.
- Remplacement de l'appel `pytest` par `python -m pytest`.
- Ajout de `tests/conftest.py` pour ajouter explicitement la racine du depot a
  `sys.path`.
- Ajout de `docs/explication_pipeline.md`.
- Mise a jour de `docs/rapport_final.md` avec l'explication du pipeline, du
  probleme de test et du comportement V1/V2.
- Generation prevue du rapport court en DOCX et PDF.

## Verification locale

Commande executee localement :

```powershell
venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

Resultat :

```text
21 passed
```

Une alerte de cache pytest est apparue dans l'environnement Codex car le sandbox
ne pouvait pas ecrire dans `.pytest_cache`. Cette alerte n'est pas liee au
probleme GitLab.

## Reponse courte pour la soutenance

Le pipeline a echoue au stage `test` car pytest ne trouvait pas le module `src`
dans l'environnement Docker de GitLab CI. La correction consiste a rendre la
racine du depot explicite avec `PYTHONPATH`, a lancer pytest via `python -m
pytest`, et a ajouter un `conftest.py` qui securise les imports pendant les
tests.

## Points a verifier ensuite

- Relancer le pipeline GitLab apres commit/push.
- Verifier que le stage `test` passe.
- Verifier que les stages `build`, `scan`, `push` et `deploy` demarrent ensuite.
- Faire une capture de FastAPI `/docs`.
- Faire une capture MLflow si MLflow est lance localement.
- Verifier que le rapport DOCX/PDF est bien present dans `docs/`.
