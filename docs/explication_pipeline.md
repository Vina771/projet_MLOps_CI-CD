# Explication du pipeline GitLab CI/CD

Ce document explique le role de chaque etape du pipeline actuel. Il sert de
support court pour la soutenance.

## Resume des stages

Le pipeline contient six stages executes dans cet ordre :

1. `lint`
2. `test`
3. `build`
4. `scan`
5. `push`
6. `deploy`

Si un stage echoue, les stages suivants ne sont pas executes. C'est ce qui est
arrive dans le pipeline : le stage `test` a echoue, donc `build`, `scan`,
`push` et `deploy` ont ete bloques.

## Stage lint

Le lint est un controle automatique de qualite du code.

Dans ce projet, il utilise deux outils :

- `flake8` : detecte des problemes de style Python et certaines erreurs simples
  comme des imports inutilises, des noms incorrects ou des lignes trop longues.
- `black --check` : verifie que le code est formate selon le format Black.

Le lint ne lance pas l'application et n'entraine pas le modele. Son role est de
refuser un code mal formate ou suspect avant de perdre du temps sur les tests et
les images Docker.

## Stage test

Le stage `test` installe les dependances Python, telecharge les ressources NLTK,
puis lance pytest.

Il verifie notamment :

- les fonctions de preprocessing NLP ;
- le chargement ou l'entrainement minimal du modele ;
- les endpoints FastAPI `/health`, `/predict` et `/metrics` ;
- la presence des fichiers importants du projet ;
- la configuration attendue du pipeline.

Ce stage produit deux artefacts GitLab :

- `test-results.xml` pour le rapport de tests ;
- `coverage.xml` pour la couverture de code.

## Correction du probleme de test

Le pipeline echouait avec l'erreur suivante :

```text
ModuleNotFoundError: No module named 'src'
```

La cause probable est que, dans l'image Docker `python:3.11-slim` utilisee par
GitLab CI, la racine du depot n'etait pas toujours presente dans le chemin
d'import Python pendant la collecte pytest.

La correction appliquee est double :

- ajout de `PYTHONPATH: "$CI_PROJECT_DIR"` dans `.gitlab-ci.yml` ;
- ajout de `tests/conftest.py`, qui ajoute explicitement la racine du projet a
  `sys.path` pour tous les tests.

Le job lance aussi maintenant les tests avec :

```bash
python -m pytest tests/ -v --tb=short --junit-xml=test-results.xml --cov=src --cov-report=xml
```

Cette forme est plus robuste que l'appel direct `pytest`, car elle utilise le
module Python courant et conserve mieux le contexte d'import.

## Stage build

Le stage `build` construit deux images Docker :

- l'image Streamlit : `ghcr.io/vina771/projet11-mlops` ;
- l'image FastAPI : `ghcr.io/vina771/projet11-fastapi`.

Chaque image recoit deux tags :

- `$CI_PIPELINE_ID`, pour garder une version precise du pipeline ;
- `latest`, pour pointer vers la derniere version publiee.

## Stage scan

Le stage `scan` utilise Trivy pour analyser les images Docker et afficher les
vulnerabilites HIGH et CRITICAL.

Dans ce projet, `--exit-code 0` permet de garder la demonstration fluide : le
rapport de securite est visible dans les logs, mais le pipeline ne bloque pas
uniquement a cause d'une vulnerabilite trouvee dans une dependance de base.

## Stage push

Le stage `push` se connecte a GHCR avec les variables GitLab :

- `GHCR_USER`
- `GHCR_TOKEN`
- `REGISTRY`

Il pousse ensuite les deux images, avec leurs tags `$CI_PIPELINE_ID` et
`latest`, vers GitHub Container Registry.

## Stage deploy

Le stage `deploy` lance Ansible. Le playbook actuel se connecte a GHCR, pull
l'image Streamlit et relance le conteneur `projet11_streamlit`.

Important : dans l'etat actuel, le deploiement Ansible automatise surtout
Streamlit. FastAPI est construite et poussee dans GHCR, mais le deploiement
complet des deux services doit etre fait via Docker Compose ou par une extension
du playbook Ansible.

## Que se passe-t-il si V2 echoue ?

Oui, l'idee CI/CD est la suivante : une nouvelle version ne doit etre deployee
que si les controles obligatoires passent.

Dans ce pipeline, si la V2 echoue au stage `test`, alors :

- les images V2 ne sont pas construites ;
- elles ne sont pas poussees dans GHCR ;
- le stage `deploy` ne s'execute pas ;
- la version deja deployee, par exemple V1, reste en place.

Si la V2 passe les tests, mais echoue plus tard au `build`, au `push` ou au
`deploy`, la situation depend du point exact de l'echec. Comme le deploiement
n'a lieu qu'a la fin, V1 reste normalement active tant que le conteneur n'est
pas remplace avec succes.

Pour rendre cette logique encore plus solide, on peut deployer avec le tag
`$CI_PIPELINE_ID` et garder `latest` comme alias, puis ajouter une verification
healthcheck apres deploiement. Si le healthcheck echoue, on peut revenir a
l'image precedente.
