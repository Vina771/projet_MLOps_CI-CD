$GHCR_USERNAME     = "Vina771"
$GITHUB_USERNAME   = "Vina771"
$GITHUB_REPO       = "projet_MLOps_CI-CD"
$GIT_EMAIL         = "raharitsifa.vina@gmail.com"
$GITHUB_REPO_URL   = "https://github.com/${GITHUB_USERNAME}/${GITHUB_REPO}.git"
$GHCR_IMAGE        = "ghcr.io/vina771/projet11-mlops"

Write-Host ""
Write-Host "Projet MLOps CI/CD - Setup GitLab + GHCR" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/6] Verification des outils..." -ForegroundColor Yellow

try { docker --version | Out-Null; Write-Host "  Docker OK" -ForegroundColor Green }
catch { Write-Host "  ERREUR : Docker non disponible" -ForegroundColor Red; exit 1 }

try { git --version | Out-Null; Write-Host "  Git OK" -ForegroundColor Green }
catch { Write-Host "  ERREUR : Git non disponible" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "[2/6] Preparation des dossiers locaux..." -ForegroundColor Yellow

@("models", "outputs", "reports", "tests", "ansible", "src", "docker", "monitoring") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ | Out-Null }
}

Write-Host "  Dossiers OK" -ForegroundColor Green

Write-Host ""
Write-Host "[3/6] Lancement de l infrastructure GitLab..." -ForegroundColor Yellow
Write-Host "  Attention : GitLab prend 3-5 minutes au premier demarrage"

docker-compose -f docker-compose.infra.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERREUR : lancement de l infrastructure echoue" -ForegroundColor Red
    exit 1
}

Write-Host "  Infrastructure lancee" -ForegroundColor Green
Write-Host "  GitLab : http://localhost:8929"
Write-Host "  Runner : conteneur gitlab-runner"

Write-Host ""
Write-Host "[4/6] Informations GitLab..." -ForegroundColor Yellow
Write-Host "  Mot de passe GitLab root initial :"
docker exec gitlab cat /etc/gitlab/initial_root_password 2>$null |
    Select-String "Password:" | ForEach-Object { Write-Host "    $_" -ForegroundColor White }

Write-Host ""
Write-Host "[5/6] Initialisation Git locale..." -ForegroundColor Yellow

git config --global user.name  $GITHUB_USERNAME
git config --global user.email $GIT_EMAIL

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

$filesToAdd = @(
    ".gitignore", ".env.example", ".gitlab-ci.yml", "README.md", "requirements.txt",
    "app_streamlit.py", "setup_models.py", "Dockerfile.streamlit",
    "docker-compose.infra.yml", "docker-compose.yml",
    "ansible/playbook.yml", "ansible/inventory.ini",
    "src/app.py", "src/train.py", "src/predict.py",
    "docker/Dockerfile",
    "monitoring/prometheus.yml", "monitoring/grafana/dashboards/mlops.json",
    "monitoring/grafana/provisioning/datasources/prometheus.yml",
    "monitoring/grafana/provisioning/dashboards/dashboards.yml",
    "tests/test_pipeline.py", "tests/test_api.py", "tests/test_train.py",
    "docs/cahier_des_charges.md", "docs/architecture.md", "docs/rapport_final.md",
    "RESUME_ACTIONS_GHCR.txt", "SUIVI_CODEX_GHCR.md"
)

foreach ($file in $filesToAdd) {
    if (Test-Path $file) { git add $file }
}

git commit -m "Projet MLOps CI/CD GitLab GHCR"

$remoteExists = git remote get-url github 2>$null
if ($remoteExists) {
    git remote set-url github $GITHUB_REPO_URL
} else {
    git remote add github $GITHUB_REPO_URL
}

Write-Host "  Git local pret" -ForegroundColor Green
Write-Host "  Miroir GitHub : $GITHUB_REPO_URL"
Write-Host "  Image GHCR : $GHCR_IMAGE"

Write-Host ""
Write-Host "[6/6] Configuration manuelle restante..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  A. Enregistrer le runner dans GitLab si necessaire :" -ForegroundColor White
Write-Host "     docker exec -it gitlab-runner gitlab-runner register"
Write-Host "     URL : http://gitlab:80"
Write-Host "     Executor : docker"
Write-Host "     Image par defaut : python:3.11-slim"
Write-Host "     Verifier que /var/run/docker.sock est monte"
Write-Host ""
Write-Host "  B. Configurer GitHub Container Registry :" -ForegroundColor White
Write-Host "     Creer un GitHub PAT avec write:packages et read:packages"
Write-Host "     Image cible : $GHCR_IMAGE"
Write-Host ""
Write-Host "  C. Configurer les variables GitLab CI/CD :" -ForegroundColor White
Write-Host "     REGISTRY=ghcr.io"
Write-Host "     IMAGE_NAME=$GHCR_IMAGE"
Write-Host "     GHCR_USER=$GHCR_USERNAME"
Write-Host "     GHCR_TOKEN=(GitHub PAT packages, masked/protected)"
Write-Host ""
Write-Host "  D. Tester le pipeline :" -ForegroundColor White
Write-Host "     git push gitlab main"
Write-Host "     git push github main"
Write-Host ""
Write-Host "Setup termine !" -ForegroundColor Green
