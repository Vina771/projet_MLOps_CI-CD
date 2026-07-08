# Suivi Codex - migration GHCR

## 2026-07-06 - Decision

Objectif utilisateur : ne plus utiliser de registry local auto-heberge, migrer vers GitHub Container Registry.

## Etat apres cette passe

Fait :
- Contexte projet `CONTEXTE_PROJET_MLOPS_v2.txt` migre en version 3 GHCR.
- `.gitlab-ci.yml` migre vers `ghcr.io/vina771/projet11-mlops`.
- `ansible/playbook.yml` migre vers `REGISTRY`, `IMAGE_NAME`, `GHCR_USER`, `GHCR_TOKEN`.
- `.env.example`, README, docs et script setup mis a jour.
- Ancien resume registry remplace par `RESUME_ACTIONS_GHCR.txt`.

A faire / verifier :
- Configurer dans GitLab CI/CD : `REGISTRY`, `IMAGE_NAME`, `GHCR_USER`, `GHCR_TOKEN`.
- Creer un GitHub PAT avec `write:packages` et `read:packages`.
- Verifier que le GitLab Runner est enregistre avec acces Docker socket.
- Lancer un pipeline complet.
- Confirmer que l'image apparait dans GitHub Packages.

Point d'attention :
- Le stage `scan` scanne l'image Docker locale via Trivy. Cela suppose que le runner partage le Docker daemon entre jobs via `/var/run/docker.sock`, comme prevu dans le projet.

## 2026-07-07 - Installation et verification locale

Fait :
- Docker Desktop verifie : Docker 29.6.1, Docker Compose v5.3.0.
- GitLab CE lance et healthy sur `http://localhost:8929`.
- GitLab Runner lance et enregistre : `mlops-docker-runner`, executor Docker.
- Runner verifie avec `volumes = ["/var/run/docker.sock:/var/run/docker.sock", "/cache"]`.
- `venv` cree en Python 3.12, faute de Python 3.11 installe sur Windows.
- Dependances Python installees : `requirements.txt`, `pytest`, `pytest-cov`, `flake8`, `black`, `httpx`.
- Ressources NLTK installees : `punkt`, `stopwords`, `wordnet`, `omw-1.4`, `punkt_tab`.
- Modeles telecharges dans `models/` : `best_model.pkl`, `tfidf_vectorizer.pkl`.
- Fichiers Python reformates avec Black et corrections flake8 appliquees.
- `docker-compose.yml` aligne sur les images GHCR locales.
- Provisioning Grafana ajoute pour datasource Prometheus + dashboard.
- Images Docker locales construites :
  - `ghcr.io/vina771/projet11-mlops:local`
  - `ghcr.io/vina771/projet11-fastapi:local`
- Services lances : Streamlit, FastAPI, Prometheus, Grafana.

Validations :
- `pytest tests/ -q` : 21 passed.
- `black --check src tests app_streamlit.py setup_models.py` : OK.
- `flake8 src tests app_streamlit.py setup_models.py --max-line-length=120 --ignore=E501,W503 --exclude=venv,__pycache__,.cache` : OK.
- FastAPI `/health` : OK, model_exists=true, tfidf_exists=true.
- FastAPI `/predict` : OK, prediction positive testee.
- Streamlit health : OK.
- Prometheus `/-/ready` : OK.
- Grafana `/api/health` : OK, database ok.

A faire :
- Creer le token GitHub PAT pour GHCR.
- Configurer les variables GitLab CI/CD.
- Creer/verifier le projet GitLab local et pousser le depot.
- Lancer et valider le pipeline GitLab complet.
- Verifier le push final de l'image `ghcr.io/vina771/projet11-mlops:latest`.

## 2026-07-08 - Documentation de reprise et justification

Fait :
- Token GitHub classic signale par l'utilisateur, mais volontairement non ecrit dans le depot.
- README complete avec un tableau outils / role / justification.
- `docs/outils_et_choix.md` cree pour le rapport et la soutenance.
- Justification des deux fichiers Compose ajoutee dans README, architecture et reste a faire.
- `CONTEXTE_PROJET_MLOPS_v2.txt` passe en version 5 avec l'etat de reprise.

A faire maintenant :
- Ajouter le token dans GitLab CI/CD sous `GHCR_TOKEN`, masked.
- Verifier ou creer les variables `REGISTRY`, `IMAGE_NAME`, `GHCR_USER`, `GHCR_TOKEN`.
- Pousser le depot local vers GitLab CE local si ce n'est pas deja fait.
- Lancer un pipeline complet et verifier les 6 stages.
- Verifier que l'image `ghcr.io/vina771/projet11-mlops:latest` apparait dans GitHub Packages.
