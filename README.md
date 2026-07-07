# Projet MLOps CI/CD avec Docker, GitLab et GHCR

Projet MLOps de deploiement du Projet 11 NLP : analyse de sentiment sur des tweets politiques avec un modele LinearSVC + TF-IDF bigrammes.

## Architecture cible

```text
Push GitLab CE local
  -> GitLab CI/CD + GitLab Runner
  -> lint -> test -> build Docker -> scan Trivy -> push GHCR -> deploy Ansible
  -> Streamlit http://localhost:8501
  -> FastAPI http://localhost:8000
  -> Prometheus http://localhost:9090
  -> Grafana http://localhost:3000
```

GitHub sert de miroir public pour le rendu et GitHub Container Registry (GHCR) sert de registry Docker principal. Streamlit Cloud reste disponible comme demo publique.

## Services

| Service | Role | URL |
|---|---|---|
| GitLab CE | Depot principal et pipelines | http://localhost:8929 |
| GitLab Runner | Execution des jobs CI/CD | conteneur Docker |
| GHCR | Registry Docker principal | ghcr.io/vina771/projet11-mlops |
| Streamlit | Dashboard de demo | http://localhost:8501 |
| FastAPI | API de prediction + metriques | http://localhost:8000 |
| Prometheus | Scrape `/metrics` FastAPI | http://localhost:9090 |
| Grafana | Dashboard monitoring | http://localhost:3000 |

## Configuration GHCR

Creer un token GitHub personnel avec les permissions packages :

- `write:packages`
- `read:packages`

Configurer ensuite les variables GitLab CI/CD dans `Settings -> CI/CD -> Variables` :

| Variable | Valeur |
|---|---|
| `REGISTRY` | `ghcr.io` |
| `IMAGE_NAME` | `ghcr.io/vina771/projet11-mlops` |
| `GHCR_USER` | `Vina771` |
| `GHCR_TOKEN` | token GitHub, masked/protected |

Test manuel possible :

```powershell
echo VOTRE_TOKEN | docker login ghcr.io -u Vina771 --password-stdin
docker build -f Dockerfile.streamlit -t ghcr.io/vina771/projet11-mlops:test .
docker push ghcr.io/vina771/projet11-mlops:test
```

## Lancement local

```powershell
docker-compose -f docker-compose.infra.yml up -d
docker-compose up -d
```

Verifier :

```powershell
pytest tests/ -v
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

Etat verifie le 2026-07-07 :

- GitLab CE et GitLab Runner tournent localement.
- Le runner `mlops-docker-runner` est enregistre avec l'executor Docker et le socket `/var/run/docker.sock`.
- `venv` est installe en Python 3.12 avec les dependances du projet.
- Les modeles `best_model.pkl` et `tfidf_vectorizer.pkl` sont telecharges dans `models/`.
- Les images locales `ghcr.io/vina771/projet11-mlops:local` et `ghcr.io/vina771/projet11-fastapi:local` sont construites.
- Streamlit, FastAPI, Prometheus et Grafana sont lances via Docker Compose.
- Grafana provisionne automatiquement la datasource Prometheus et le dashboard `Projet 11 MLOps`.
- `pytest tests/ -q`, `black --check` et `flake8` passent localement.

## Pipeline GitLab CI/CD

Le fichier `.gitlab-ci.yml` contient 6 stages :

1. `lint` : flake8 + black
2. `test` : pytest + coverage
3. `build` : build de l'image Docker Streamlit
4. `scan` : scan Trivy HIGH/CRITICAL
5. `push` : push vers GHCR
6. `deploy` : deploiement via Ansible

L'image finale attendue est :

```text
ghcr.io/vina771/projet11-mlops:latest
```

## Justification registry

Le projet utilise GHCR pour eviter la maintenance d'un registry local sous Windows/WSL2. Le critere registry reste couvert par un registry professionnel integre a GitHub, et le scan securite reste assure par Trivy dans le pipeline GitLab CI/CD.

## Auteur

Vina - Master 1 IA & Data Science, INSI Madagascar

## Suite manuelle

Les etapes restantes sont detaillees dans `docs/reste_a_faire.md` : creation du token GHCR, variables GitLab CI/CD, push GitLab/GitHub et test du pipeline complet.
