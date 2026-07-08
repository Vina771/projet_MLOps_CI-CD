# Outils utilises et justification des choix

Ce document sert de support pour le rapport et la soutenance. Il explique le role de chaque outil et pourquoi il a ete retenu dans cette version du projet MLOps CI/CD.

## Tableau des outils

| Outil | Role dans le projet | Pourquoi ce choix |
|---|---|---|
| Git | Versionnement local du code | Indispensable pour suivre les changements, creer un historique propre et pousser vers GitLab/GitHub. |
| GitLab CE | Depot principal local et interface CI/CD | Correspond au sujet, permet de montrer un pipeline complet dans un environnement controle. |
| GitLab CI/CD | Orchestration du pipeline | Automatise les etapes `lint`, `test`, `build`, `scan`, `push` et `deploy`. |
| GitLab Runner | Execution des jobs CI/CD | Execute les jobs dans des conteneurs Docker et accede au Docker daemon via `/var/run/docker.sock`. |
| GitHub | Depot public de rendu | Permet de rendre le projet visible publiquement et de lier le code au registry GHCR. |
| GHCR | Registry Docker principal | Remplace Harbor par un registry professionnel integre a GitHub, plus simple a maintenir sur Windows 11 + Docker Desktop. |
| Docker | Containerisation de l'application | Garantit un environnement reproductible pour Streamlit, FastAPI et le deploiement CI/CD. |
| Dockerfile.streamlit | Image de l'interface Streamlit | Separe le packaging de l'interface utilisateur du packaging API. |
| docker/Dockerfile | Image de l'API FastAPI | Permet de lancer l'API ML et les metriques dans un conteneur dedie. |
| Docker Compose | Orchestration locale des services | Lance plusieurs conteneurs avec reseau, volumes, ports et variables coherents. |
| docker-compose.infra.yml | GitLab CE + GitLab Runner | Isole l'infrastructure CI/CD, lourde et persistante, de l'application. |
| docker-compose.yml | Streamlit + FastAPI + Prometheus + Grafana | Isole l'application MLOps, qui est reconstruite et relancee plus souvent. |
| Ansible | Deploiement automatise | Pull l'image GHCR et relance le conteneur Streamlit depuis le stage `deploy`. |
| Python 3.11 | Runtime cible Docker/CI | Version demandee par le sujet et compatible avec FastAPI, scikit-learn et les tests. |
| Python 3.12 local | Venv de validation Windows | Utilise localement car Python 3.11 n'est pas installe sur la machine ; Docker/CI restent en Python 3.11. |
| scikit-learn | Modele ML | Sert au pipeline NLP avec LinearSVC et TF-IDF. |
| NLTK | Pretraitement NLP | Fournit les ressources de tokenisation, stopwords et normalisation utilisees par le projet. |
| joblib | Chargement des artefacts modele | Charge `best_model.pkl` et `tfidf_vectorizer.pkl`. |
| gdown | Recuperation des modeles | Telecharge les artefacts `.pkl` depuis Google Drive sans les committer. |
| FastAPI | API de prediction | Expose `/health`, `/predict`, `/predict/batch` et `/metrics`. |
| Uvicorn | Serveur ASGI FastAPI | Lance l'API dans le conteneur. |
| Streamlit | Interface de demonstration | Donne une demo visuelle simple pour la soutenance et les tests utilisateurs. |
| pytest | Tests automatises | Verifie les fonctions ML, l'API et le pipeline applicatif. |
| pytest-cov | Couverture de tests | Produit `coverage.xml` pour GitLab CI/CD. |
| flake8 | Controle qualite Python | Detecte les erreurs de style et certains problemes statiques. |
| Black | Formatage Python | Rend le code homogene et evite les debats de style. |
| Trivy | Scan de vulnerabilites | Couvre l'exigence securite du sujet, avec rapport visible dans le stage `scan`. |
| Prometheus | Collecte des metriques | Scrape `/metrics` expose par FastAPI. |
| Grafana | Visualisation monitoring | Affiche un dashboard MLOps provisionne automatiquement. |
| .env.example | Modele de configuration | Documente les variables sans exposer de secret reel. |

## Justification des deux fichiers Docker Compose

Le sujet recommande un `docker-compose.yml` pour le deploiement applicatif. Dans ce projet, il y a deux fichiers Compose pour separer deux responsabilites qui n'ont pas le meme cycle de vie.

`docker-compose.infra.yml` sert uniquement a l'infrastructure CI/CD locale :

- GitLab CE ;
- GitLab Runner ;
- volumes persistants GitLab ;
- acces Docker socket pour le runner.

Ces services sont lourds, longs a demarrer et doivent rester stables. Les relancer a chaque changement applicatif ferait perdre du temps et pourrait interrompre les pipelines.

`docker-compose.yml` sert a l'application MLOps :

- Streamlit ;
- FastAPI ;
- Prometheus ;
- Grafana ;
- volumes modeles et dashboards ;
- reseau applicatif.

Ces services sont reconstruits et verifies souvent pendant le developpement. Les separer de GitLab rend les commandes plus simples et les demonstrations plus propres.

## Phrase courte pour la soutenance

Le projet utilise deux Compose par separation des responsabilites : un Compose d'infrastructure pour GitLab et le runner CI/CD, et un Compose applicatif pour le deploiement MLOps. Cette separation evite de redemarrer GitLab inutilement et rend la demo plus claire.

## Pourquoi GHCR au lieu de Harbor

Le sujet initial cite Harbor comme registry prive avec scan securite. La version finale remplace Harbor par GHCR pour reduire la complexite sous Windows 11 + Docker Desktop + WSL2.

Le critere registry reste couvert par :

- build d'image Docker ;
- scan Trivy ;
- authentification par token ;
- push vers un registry professionnel ;
- pull/deploiement depuis le registry.

Le scan securite n'est pas perdu : il est effectue explicitement par Trivy dans GitLab CI/CD.
