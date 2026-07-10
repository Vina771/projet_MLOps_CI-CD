# Rapport final - Projet MLOps CI/CD

## 1. Resume du projet

Ce projet met en place une chaine MLOps CI/CD pour deployer une application de Machine Learning de sentiment analysis appliquee a des tweets politiques. Le modele vient du Projet 11 NLP et repose sur une vectorisation TF-IDF avec un classifieur LinearSVC. L'objectif n'est pas seulement de fournir un modele, mais de montrer tout le cycle industriel autour de ce modele : tests, qualite, containerisation, securite, publication d'image et deploiement.

L'enonce initial demande GitLab CI/CD, Docker, Docker Compose, FastAPI, Trivy et Harbor. Dans cette version, Harbor est utilise comme registry Docker local/offline. Ce choix reduit la dependance au Wi-Fi : les images sont construites, scannees, poussees dans Harbor, puis tirees pendant le deploiement local.

## 2. Application ML

Le cas d'usage est une analyse de sentiment de tweets politiques avec trois classes : negative, neutral et positive. Le modele de reference utilise :

- un nettoyage NLP des textes ;
- une vectorisation TF-IDF avec bigrammes ;
- un modele LinearSVC ;
- un score de reference F1 test de 0.8902.

Le projet expose deux surfaces applicatives. FastAPI est le service ML central : il fournit `/health`, `/predict`, `/predict/batch`, `/metrics` et `/docs`. Streamlit sert d'interface de demonstration et appelle FastAPI via la variable `API_BASE_URL`. Si FastAPI est indisponible pendant une demo locale, Streamlit garde un fallback vers le modele local.

## 3. Architecture technique

L'architecture finale est organisee autour de GitLab CE local, GitLab Runner, Docker, Harbor, Ansible, Streamlit, FastAPI, Prometheus et Grafana.

Le flux cible est le suivant :

```text
Code ML
  -> push GitLab CE local
  -> pipeline GitLab CI/CD
  -> lint, test, build, scan, push, deploy
  -> images Docker dans Harbor
  -> deploiement local
  -> Streamlit, FastAPI, Prometheus, Grafana
```

Deux fichiers Docker Compose sont utilises. `docker-compose.infra.yml` lance la plateforme CI/CD locale, c'est-a-dire GitLab CE et GitLab Runner. Ces services sont lourds et persistants. `docker-compose.yml` lance l'application MLOps : Streamlit, FastAPI, Prometheus et Grafana. Cette separation evite de redemarrer GitLab quand on veut seulement tester l'application.

## 4. Pipeline CI/CD

Le pipeline contient six stages principaux : `lint`, `test`, `build`, `scan`, `push` et `deploy`, puis un stage `cleanup` pour nettoyer les tags CI temporaires et le cache Docker du runner.

Le stage `lint` controle la qualite du code avant les tests. Il utilise `flake8` pour detecter des erreurs de style ou des problemes simples, et `black --check` pour verifier que le formatage Python est homogene.

Le stage `test` installe les dependances Python, telecharge les ressources NLTK et lance pytest. Les tests couvrent le preprocessing NLP, l'entrainement minimal, les endpoints FastAPI et la presence des fichiers importants du projet. Il genere aussi `test-results.xml` et `coverage.xml`.

Le stage `build` construit deux images Docker : l'image Streamlit `host.docker.internal:8080/projet-mlops/projet11-mlops` et l'image FastAPI `host.docker.internal:8080/projet-mlops/projet11-fastapi`. Chaque image recoit un tag `$CI_PIPELINE_ID` pour la tracabilite et un tag `latest` pour la derniere version.

Le stage `scan` utilise Trivy pour analyser les vulnerabilites HIGH et CRITICAL. Le stage `push` se connecte a Harbor avec les variables GitLab CI/CD et pousse les deux images. Le stage `deploy` lance Ansible pour tirer l'image depuis Harbor et relancer le conteneur de deploiement.

## 5. Probleme rencontre et correction

Le pipeline GitLab a echoue au stage `test` avec l'erreur :

```text
ModuleNotFoundError: No module named 'src'
```

Cette erreur arrive pendant la collecte pytest, quand `tests/test_api.py` tente d'importer l'application avec `from src import app as api`. Dans l'environnement GitLab CI, la racine du depot n'etait pas garantie dans le chemin d'import Python.

La correction appliquee rend ce chemin explicite :

- ajout de `PYTHONPATH: "$CI_PROJECT_DIR"` dans `.gitlab-ci.yml` ;
- ajout de `tests/conftest.py` pour ajouter la racine du projet a `sys.path` ;
- remplacement de `pytest ...` par `python -m pytest ...` dans le job GitLab.

## 6. Registry, securite et secrets

Le registry final est Harbor. Les images attendues sont :

- `host.docker.internal:8080/projet-mlops/projet11-mlops:latest`
- `host.docker.internal:8080/projet-mlops/projet11-fastapi:latest`

Les secrets ne sont pas commites dans le depot. Le mot de passe Harbor doit etre place uniquement dans GitLab CI/CD, dans les variables masquees :

- `REGISTRY`
- `HARBOR_PROJECT`
- `IMAGE_NAME`
- `FASTAPI_IMAGE_NAME`
- `REGISTRY_USER`
- `REGISTRY_PASSWORD`

Trivy fournit le controle securite dans le pipeline. Harbor fournit le registry local, et l'ensemble reste demonstrable sans registry cloud.

## 7. Deploiement et comportement V1/V2

Le principe de CI/CD est que la version deployee ne doit etre remplacee que si les controles obligatoires passent. Si une V1 fonctionne et qu'une V2 echoue au stage `test`, la V2 n'est pas construite, pas poussee et pas deployee. La V1 reste donc en place.

Si la V2 passe les tests mais echoue au build, au push ou au deploy, le deploiement final ne se termine pas. Comme le remplacement du conteneur arrive a la fin, l'ancienne version reste normalement active tant que la nouvelle n'est pas relancee avec succes.

Dans l'etat actuel, le playbook Ansible automatise surtout le redeploiement du conteneur Streamlit. FastAPI est bien construite et poussee dans Harbor, mais un deploiement complet des deux services peut aussi etre fait via Docker Compose.

## 8. Monitoring et demonstration

FastAPI expose les metriques Prometheus sur `/metrics`. Prometheus collecte ces metriques et Grafana les affiche dans un dashboard provisionne automatiquement. Les URLs locales de demonstration sont :

- Streamlit : `http://localhost:8501`
- FastAPI : `http://localhost:8000`
- FastAPI docs : `http://localhost:8000/docs`
- Prometheus : `http://localhost:9090`
- Grafana : `http://localhost:3000`
- Harbor : `http://localhost:8080`

Les captures recommandees pour le rendu sont :

- capture du pipeline GitLab avec les six stages principaux et le cleanup ;
- capture du projet Harbor `projet-mlops` avec les deux images ;
- capture du job `test` corrige ;
- capture de FastAPI `/docs` ;
- capture Streamlit ;
- capture Prometheus ou Grafana.

## 9. Conclusion

Le projet couvre les criteres principaux du sujet : pipeline CI/CD, tests automatises, containerisation Docker, scan de vulnerabilites, registry Harbor, deploiement automatise et documentation. L'utilisation de Harbor local/offline rend la demonstration plus autonome tout en conservant la logique MLOps attendue : chaque modification de code passe par des controles avant de pouvoir produire et deployer une nouvelle image.