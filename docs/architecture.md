# Architecture - Projet MLOps CI/CD

## Flux CI/CD

```text
Developpeur
  -> push GitLab CE local
  -> GitLab Runner
  -> lint / test / build / scan / push / deploy
  -> GHCR
  -> deploiement Streamlit
```

## Registry

| Element | Valeur |
|---|---|
| Registry | `ghcr.io` |
| Image | `ghcr.io/vina771/projet11-mlops` |
| Tags | `latest` et `$CI_PIPELINE_ID` |
| Authentification CI | `GHCR_USER` + `GHCR_TOKEN` |

## Services applicatifs

- Streamlit : interface utilisateur du Projet 11 NLP.
- FastAPI : endpoint `/predict`, `/predict/batch`, `/health`, `/metrics`.
- Prometheus : collecte les metriques FastAPI toutes les 15 secondes.
- Grafana : visualise trafic, latence, erreurs et repartition des sentiments.

## Monitoring Grafana

Grafana est provisionne automatiquement au demarrage :

- datasource : `monitoring/grafana/provisioning/datasources/prometheus.yml`
- dashboard provider : `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- dashboard JSON : `monitoring/grafana/dashboards/mlops.json`

Identifiants locaux Grafana :

- URL : `http://localhost:3000`
- utilisateur : `admin`
- mot de passe : `admin`

## Securite et qualite

- Les secrets restent dans les variables GitLab CI/CD masked/protected.
- Trivy scanne l'image avant le push.
- GHCR stocke les images versionnees du pipeline.
- Les artefacts lourds ne sont pas commits.
- Les tests et le lint s'executent a chaque pipeline.
