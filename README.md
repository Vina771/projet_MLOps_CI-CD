# Projet MLOps CI/CD avec Docker, GitLab et Harbor

Projet MLOps de deploiement du Projet 11 NLP : analyse de sentiment sur des tweets politiques avec un modele LinearSVC + TF-IDF bigrammes.

## Architecture cible

```text
Push GitLab CE local
  -> GitLab CI/CD + GitLab Runner
  -> lint -> test -> build Docker -> scan Trivy -> push Harbor -> deploy Ansible
  -> images Streamlit + FastAPI publiees dans Harbor local
  -> Streamlit http://localhost:8501
  -> FastAPI http://localhost:8000
  -> Prometheus http://localhost:9090
  -> Grafana http://localhost:3000
```

GitHub reste le miroir public pour le rendu du code. Harbor devient le registry Docker principal afin de reduire la dependance au Wi-Fi pendant les builds, push et deploys locaux.

## Services

| Service | Role | URL |
|---|---|---|
| GitLab CE | Depot principal et pipelines | http://localhost:8929 |
| GitLab Runner | Execution des jobs CI/CD | conteneur Docker |
| Harbor | Registry Docker local/offline | http://localhost:8080 |
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
| Harbor | Registry Docker local principal | Conforme au sujet et permet de pousser/tirer les images sans dependre d'un registry cloud. |
| Trivy | Scan de vulnerabilites de l'image Docker | Couvre l'exigence securite avec un rapport visible dans GitLab CI/CD. |
| Ansible | Redeploiement automatise depuis le pipeline | Automatise le pull depuis Harbor et le redemarrage du conteneur de deploiement. |
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

## Configuration Harbor

Le dossier offline Harbor est deja present ici :

```text
C:\Users\Vina\Documents\Harbor\harbor
```

Sa configuration actuelle expose Harbor en HTTP sur `http://localhost:8080`. Pour un usage local, les images du projet utilisent :

```text
host.docker.internal:8080/projet-mlops/projet11-mlops
host.docker.internal:8080/projet-mlops/projet11-fastapi
```

Variables GitLab CI/CD a configurer dans `Settings -> CI/CD -> Variables` :

| Variable | Valeur |
|---|---|
| `REGISTRY` | `localhost:8080` |
| `HARBOR_PROJECT` | `projet-mlops` |
| `IMAGE_NAME` | `host.docker.internal:8080/projet-mlops/projet11-mlops` |
| `FASTAPI_IMAGE_NAME` | `host.docker.internal:8080/projet-mlops/projet11-fastapi` |
| `REGISTRY_USER` | `admin` |
| `REGISTRY_PASSWORD` | mot de passe Harbor, masked/protected |


Pour reduire encore plus la dependance au reseau, les images de jobs CI sont miroirisees dans Harbor et utilisees par defaut :

| Variable | Valeur par defaut (Harbor) | Image source d'origine |
|---|---|---|
| `PYTHON_CI_IMAGE` | `host.docker.internal:8080/projet-mlops/python:3.11-slim` | `python:3.11-slim` |
| `DOCKER_CI_IMAGE` | `host.docker.internal:8080/projet-mlops/docker:27-cli` | `docker:27-cli` |
| `TRIVY_CI_IMAGE` | `host.docker.internal:8080/projet-mlops/trivy:latest` | `aquasec/trivy:latest` |
| `ANSIBLE_CI_IMAGE` | `host.docker.internal:8080/projet-mlops/ansible:latest` | `cytopia/ansible:latest` |

Ces images doivent avoir ete miroirisees dans le projet Harbor `projet-mlops` au prealable (`docker pull` de l'image source, `docker tag` vers Harbor, `docker push`), sinon les jobs `lint`, `test`, `build` et `deploy` echoueront faute de pouvoir tirer l'image.
Le mot de passe Harbor ne doit jamais etre committe. Le mot de passe initial dans `harbor.yml` est `Harbor12345`, mais il est preferable de le changer dans l'interface Harbor apres le premier demarrage.

Commandes d'installation et de verification Harbor :

```powershell
cd C:\Users\Vina\Documents\Harbor\harbor
wsl
```

Puis dans WSL :

```bash
cd /mnt/c/Users/Vina/Documents/Harbor/harbor
sudo ./install.sh
docker compose up -d
```

Ensuite dans Windows ou WSL :

```powershell
docker login localhost:8080 -u admin
docker build -f Dockerfile.streamlit -t host.docker.internal:8080/projet-mlops/projet11-mlops:test .
docker push host.docker.internal:8080/projet-mlops/projet11-mlops:test
```

Dans l'interface Harbor, creer le projet `projet-mlops` avant le premier push si Harbor ne le cree pas automatiquement.

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

Etat local connu :

- GitLab CE et GitLab Runner tournent localement.
- Le runner `mlops-docker-runner` est enregistre avec l'executor Docker et le socket `/var/run/docker.sock`.
- `venv` est installe en Python 3.12 avec les dependances du projet.
- Les modeles `best_model.pkl` et `tfidf_vectorizer.pkl` sont telecharges dans `models/`.
- Streamlit appelle FastAPI par defaut via `API_BASE_URL` pour les predictions et garde un fallback local.
- Une page `Tester API FastAPI` permet de tester `/health`, `/metrics`, `/predict` et `/predict/batch`.
- Grafana provisionne automatiquement la datasource Prometheus et le dashboard `Projet 11 MLOps`.

## Pipeline GitLab CI/CD

Le fichier `.gitlab-ci.yml` contient 6 stages principaux et un cleanup final :

1. `lint` : flake8 + black
2. `test` : pytest + coverage
3. `build` : build des images Docker Streamlit et FastAPI
4. `scan` : scan Trivy HIGH/CRITICAL des deux images
5. `push` : push des deux images vers Harbor
6. `deploy` : deploiement via Ansible
7. `cleanup` : suppression des tags CI temporaires et nettoyage du cache Docker

Les images finales attendues sont :

```text
host.docker.internal:8080/projet-mlops/projet11-mlops:latest
host.docker.internal:8080/projet-mlops/projet11-fastapi:latest
```

## Economie de ressources Docker Desktop

`docker-compose.infra.yml` contient des reglages GitLab CE plus legers : Puma mono-processus, Sidekiq limite, Prometheus interne GitLab desactive, PostgreSQL reduit et limite memoire Docker a 4 Go pour GitLab. Cela evite de supprimer tes images/volumes tout en reduisant la pression memoire.

Pour appliquer ces reglages :

```powershell
docker compose -f docker-compose.infra.yml up -d
docker restart gitlab
```

Si Docker Desktop reste instable, arreter temporairement les services non utiles pendant le pipeline aide beaucoup :

```powershell
docker stop grafana prometheus projet11_streamlit projet11_fastapi
```

Puis relancer l'application apres le pipeline :

```powershell
docker compose up -d
```

## Auteur

Vina RAHARITSIFA - M1 I2AD, INSI