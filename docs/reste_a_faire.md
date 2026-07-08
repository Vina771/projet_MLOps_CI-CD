# Reste a faire - Projet MLOps CI/CD GHCR

Etat verifie le 2026-07-07 : l'environnement local fonctionne. GitLab CE, GitLab Runner, Streamlit, FastAPI, Prometheus et Grafana sont lances. Les tests et le lint passent.

## 1. Ajouter le token GitHub pour GHCR dans GitLab

Le token GitHub classic est maintenant disponible cote utilisateur. Ne pas le mettre dans un fichier du projet et ne pas le committer.

1. Aller dans GitLab local : `http://localhost:8929`.
2. Ouvrir le projet.
3. Aller dans Settings -> CI/CD -> Variables.
4. Ajouter `GHCR_TOKEN` avec la valeur du token GitHub classic.
5. Cocher `Masked`.
6. Cocher `Protected` seulement si le pipeline tourne sur une branche protegee comme `main`.

Test optionnel depuis PowerShell :

```powershell
echo VOTRE_TOKEN | docker login ghcr.io -u Vina771 --password-stdin
docker logout ghcr.io
```

## 2. Configurer les variables GitLab CI/CD

Dans GitLab local : `http://localhost:8929`.

1. Ouvrir le projet GitLab.
2. Aller dans Settings -> CI/CD -> Variables.
3. Ajouter :

| Variable | Valeur | Protection |
|---|---|---|
| `REGISTRY` | `ghcr.io` | non secret |
| `IMAGE_NAME` | `ghcr.io/vina771/projet11-mlops` | non secret |
| `GHCR_USER` | `Vina771` | non secret |
| `GHCR_TOKEN` | token GitHub PAT | masked, protected si la branche main est protegee |

## 3. Creer ou verifier le projet GitLab local

Dans GitLab :

1. Creer un projet vide nomme `projet_MLOps_CI-CD`.
2. Utiliser l'URL HTTP du projet, par exemple :

```text
http://localhost:8929/root/projet_MLOps_CI-CD.git
```

Depuis PowerShell dans `C:\Users\Vina\Documents\MLOps_CICD` :

```powershell
git remote add gitlab http://localhost:8929/root/projet_MLOps_CI-CD.git
git push -u gitlab main
```

Si le remote existe deja :

```powershell
git remote set-url gitlab http://localhost:8929/root/projet_MLOps_CI-CD.git
git push -u gitlab main
```

## 4. Lancer et verifier le pipeline

Dans GitLab -> CI/CD -> Pipelines, verifier les 6 stages :

1. `lint`
2. `test`
3. `build`
4. `scan`
5. `push`
6. `deploy`

Points a verifier :

- Le stage `lint` passe avec Black et flake8.
- Le stage `test` genere `coverage.xml` et `test-results.xml`.
- Le stage `build` cree les tags `$CI_PIPELINE_ID` et `latest`.
- Le stage `scan` affiche le rapport Trivy.
- Le stage `push` pousse l'image dans GHCR.
- Le stage `deploy` relance le conteneur Streamlit depuis GHCR.

## 5. Verifier GitHub Packages

Apres le pipeline :

1. Aller sur GitHub -> profil `Vina771` -> Packages.
2. Verifier l'image :

```text
ghcr.io/vina771/projet11-mlops:latest
```

3. Si le package est prive, le rendre public seulement si demande pour le rendu.

## 6. Synchroniser le depot GitHub public

Depuis PowerShell :

```powershell
git remote add github https://github.com/Vina771/projet_MLOps_CI-CD.git
git push -u github main
```

Si le remote existe deja :

```powershell
git remote set-url github https://github.com/Vina771/projet_MLOps_CI-CD.git
git push -u github main
```

## 7. Commandes de verification locale

```powershell
docker compose ps
curl.exe http://127.0.0.1:8501/_stcore/health
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:9090/-/ready
curl.exe http://127.0.0.1:3000/api/health
.\venv\Scripts\python.exe -m pytest tests/ -q
.\venv\Scripts\python.exe -m black --check src tests app_streamlit.py setup_models.py
.\venv\Scripts\python.exe -m flake8 src tests app_streamlit.py setup_models.py --max-line-length=120 --ignore=E501,W503 --exclude=venv,__pycache__,.cache
```

## 8. Points a expliquer en soutenance

- Harbor et Jenkins ne sont pas utilises dans la version finale.
- GHCR remplace Harbor comme registry professionnel.
- Trivy conserve le scan securite dans le pipeline.
- GitLab CI/CD conserve les 6 stages attendus.
- Deux fichiers Compose sont utilises par separation des responsabilites :
  - `docker-compose.infra.yml` pour GitLab CE + GitLab Runner.
  - `docker-compose.yml` pour Streamlit + FastAPI + Prometheus + Grafana.
- Cette separation evite de redemarrer l'infrastructure CI/CD pendant les tests applicatifs.
- Ansible automatise le redeploiement du conteneur Streamlit depuis GHCR.
- Prometheus scrape `/metrics` FastAPI et Grafana affiche le dashboard provisionne.

## 9. Documentation utile

- `README.md` : vue d'ensemble, lancement local, pipeline.
- `docs/architecture.md` : architecture et separation Compose.
- `docs/outils_et_choix.md` : tableau complet des outils, roles et justifications.
- `SUIVI_CODEX_GHCR.md` : historique des actions deja realisees.
