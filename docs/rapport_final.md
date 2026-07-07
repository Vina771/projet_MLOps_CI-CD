# Rapport final - Projet MLOps CI/CD

## Resume

Le projet met en place une chaine MLOps complete autour d'un modele NLP de sentiment analysis. Le pipeline reconstruit l'image Docker, lance les tests, scanne les vulnerabilites avec Trivy, publie l'image dans GHCR, puis deploie l'application.

## Modele ML

- Tache : analyse de sentiment de tweets politiques.
- Modele : LinearSVC.
- Vectorisation : TF-IDF bigrammes.
- Score de reference : F1 test 0.8902.
- Classes : negative, neutral, positive.

## Pipeline

Les 6 stages sont : lint, test, build, scan, push, deploy.

## Registry et securite

- Registry : `ghcr.io/vina771/projet11-mlops`.
- Tags : `latest` et identifiant de pipeline GitLab.
- Scan : Trivy execute dans un stage separe avant le push.
- Secrets : token GHCR stocke dans les variables GitLab CI/CD.

## Deploiement

Le deploiement local expose :

- Streamlit : `http://localhost:8501`
- FastAPI : `http://localhost:8000`
- Prometheus : `http://localhost:9090`
- Grafana : `http://localhost:3000`

## Points de demonstration

1. Montrer GitLab CE et un pipeline execute.
2. Montrer l'image dans GitHub Packages / GHCR.
3. Montrer le rapport Trivy dans les logs du stage scan.
4. Montrer l'application Streamlit locale.
5. Appeler FastAPI `/predict`.
6. Montrer les metriques dans Prometheus/Grafana.
7. Montrer le miroir GitHub public pour le rendu.
