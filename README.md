# Projet MLOps CI/CD avec Docker, GitLab et GHCR

Projet MLOps de deploiement du Projet 11 NLP : analyse de sentiment sur des tweets politiques avec un modele LinearSVC + TF-IDF bigrammes.

## Architecture cible

```text
Push GitLab CE local
  -> GitLab CI/CD + GitLab Runner
  -> lint -> test -> build Docker -> scan Trivy -> push GHCR -> deploy Ansible
  -> images Streamlit + FastAPI publiees dans GHCR
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

## Outils et justification

| Outil | Role dans le projet | Pourquoi ce choix |
|---|---|---|
| GitLab CE | Depot principal local et orchestration CI/CD | Correspond au sujet, permet de montrer un pipeline complet maitrise localement. |
| GitLab Runner | Execution des jobs `lint`, `test`, `build`, `scan`, `push`, `deploy` | Reproduit une chaine CI/CD professionnelle et pilote Docker via le socket Docker. |
| Docker | Packaging reproductible de Streamlit, FastAPI et des services de monitoring | Standard DevOps, portable entre Windows/WSL2, GitLab CI et la soutenance. |
| Docker Compose | Lancement coordonne des conteneurs | Simple pour demontrer l'infrastructure locale et l'application complete. |
| GHCR | Registry Docker principal | Remplace Harbor par un registry professionnel plus simple a maintenir sous Windows, avec push/pull authentifie. |
| Trivy | Scan de vulnerabilites de l'image Docker | Couvre l'exigence securite du sujet meme sans Harbor. |
| Ansible | Redeploiement automatise depuis le pipeline | Automatise le pull de l'image GHCR et le redemarrage du conteneur de deploiement. |
| Python 3.11 | Runtime cible dans Docker et GitLab CI | Version demandee dans le sujet et stable pour FastAPI/scikit-learn. |
| FastAPI | API ML pour `/predict`, `/predict/batch`, `/health`, `/metrics` | Leger, rapide, documente automatiquement l'API et expose facilement les metriques. |
| Streamlit | Interface de demonstration du modele NLP | Permet une demo visuelle rapide du Projet 11. |
| pytest | Tests automatises | Valide les fonctions ML, l'API et la structure avant build/push. |
| flake8 + Black | Qualite et formatage du code Python | Evite les erreurs de style et rend le code homogene. |
| Prometheus | Collecte des metriques FastAPI | Standard de monitoring simple a connecter a `/metrics`. |
| Grafana | Visualisation des metriques | Dashboard clair pour la soutenance, provisionne automatiquement. |

## Pourquoi deux fichiers Docker Compose ?

Le projet utilise deux fichiers Compose parce qu'ils n'ont pas le meme cycle de vie :

- `docker-compose.infra.yml` lance l'infrastructure CI/CD locale : GitLab CE et GitLab Runner. Ces services sont lourds, persistants, et ne doivent pas etre recrees a chaque test applicatif.
- `docker-compose.yml` lance l'application MLOps : Streamlit, FastAPI, Prometheus et Grafana. Ces services sont reconstruits et relances beaucoup plus souvent pendant le developpement et la demo.

Cette separation rend la soutenance plus claire : d'abord on montre la plateforme CI/CD, ensuite on montre l'application deployee. Elle evite aussi de redemarrer GitLab inutilement quand on veut seulement tester le modele ou le monitoring.

Le tableau detaille des outils et de leurs choix est disponible dans `docs/outils_et_choix.md`.

## Configuration GHCR

Creer un token GitHub personnel avec les permissions packages :

- `write:packages`
- `read:packages`

Configurer ensuite les variables GitLab CI/CD dans `Settings -> CI/CD -> Variables` :

| Variable | Valeur |
|---|---|
| `REGISTRY` | `ghcr.io` |
| `IMAGE_NAME` | `ghcr.io/vina771/projet11-mlops` |
| `FASTAPI_IMAGE_NAME` | `ghcr.io/vina771/projet11-fastapi` |
| `GHCR_USER` | `Vina771` |
| `GHCR_TOKEN` | token GitHub, masked/protected |

Le token GitHub personnel ne doit jamais etre committe, colle dans un fichier du projet ou affiche dans les logs.

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
- Streamlit appelle FastAPI par defaut via `API_BASE_URL` pour les predictions et garde un fallback local.
- Une page `Tester API FastAPI` permet de tester `/health`, `/metrics`, `/predict` et `/predict/batch`.
- Grafana provisionne automatiquement la datasource Prometheus et le dashboard `Projet 11 MLOps`.
- `pytest tests/ -q`, `black --check` et `flake8` passent localement.

## Pipeline GitLab CI/CD

Le fichier `.gitlab-ci.yml` contient 6 stages :

1. `lint` : flake8 + black
2. `test` : pytest + coverage
3. `build` : build des images Docker Streamlit et FastAPI
4. `scan` : scan Trivy HIGH/CRITICAL des deux images
5. `push` : push des deux images vers GHCR
6. `deploy` : deploiement via Ansible

Les images finales attendues sont :

```text
ghcr.io/vina771/projet11-mlops:latest
ghcr.io/vina771/projet11-fastapi:latest
```

## Justification registry

Le projet utilise GHCR pour eviter la maintenance d'un registry local sous Windows/WSL2. Le critere registry reste couvert par un registry professionnel integre a GitHub, et le scan securite reste assure par Trivy dans le pipeline GitLab CI/CD.

## Auteur

Vina RAHARITSIFA - M1 I2AD, INSI