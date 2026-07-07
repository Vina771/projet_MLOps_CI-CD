# Cahier des charges - Projet MLOps CI/CD

## Objectif

Mettre en place une chaine CI/CD locale pour deployer automatiquement une application NLP d'analyse de sentiment sur tweets politiques.

## Perimetre

- Depot principal : GitLab CE local.
- CI/CD : GitLab CI/CD avec GitLab Runner.
- Registry container : GitHub Container Registry (GHCR).
- Deploiement : Ansible lance depuis le pipeline.
- Monitoring : Prometheus et Grafana.
- Securite : scan Trivy dans un stage CI/CD dedie.

## Hors perimetre

- Pas de registry auto-heberge a maintenir localement.
- Pas de base de donnees applicative.
- Pas de traitement batch lourd dans le pipeline.
- Les fichiers `.pkl` et `.csv` lourds ne sont pas versionnes.

## Resultats attendus

- Pipeline 6 stages fonctionnel.
- Image poussee dans GHCR.
- Rapport Trivy visible dans les logs du pipeline.
- Application Streamlit disponible sur `http://localhost:8501`.
- API FastAPI disponible sur `http://localhost:8000`.
- Metriques Prometheus exposees sur `/metrics`.
- Dashboard Grafana disponible sur `http://localhost:3000`.
