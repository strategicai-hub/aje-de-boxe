Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsAJE : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int error) { return true; }
}
"@ -ErrorAction SilentlyContinue
[System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsAJE
[System.Net.ServicePointManager]::SecurityProtocol = "Tls,Tls11,Tls12"

$dotenv = Join-Path $env:USERPROFILE ".claude\.env"
if (-not (Test-Path $dotenv)) { Write-Error "~/.claude/.env nao encontrado" }
Get-Content $dotenv | ForEach-Object {
    if ($_ -match "^\s*([^#=\s]+)\s*=\s*(.*)$") {
        [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
    }
}
$PORTAINER_URL   = $env:PORTAINER_URL
$PORTAINER_TOKEN = $env:PORTAINER_TOKEN
if (-not $PORTAINER_URL)   { Write-Error "PORTAINER_URL nao definido" }
if (-not $PORTAINER_TOKEN) { Write-Error "PORTAINER_TOKEN nao definido" }

$IMAGE      = "ghcr.io/strategicai-hub/aje-de-boxe:latest"
$SERVICES   = @("aje-de-boxe_aje-api", "aje-de-boxe_aje-worker")
$VERIFY_URL = "https://webhook-whatsapp.strategicai.com.br/"
$projectRoot = $PSScriptRoot

Write-Host "=== [1/4] Auth GHCR ===" -ForegroundColor Cyan
$ghStatus = cmd /c "gh auth status --hostname github.com 2>&1" | Out-String
$ghUserMatch = [regex]::Match($ghStatus, "account\s+(\S+)")
if (-not $ghUserMatch.Success) { Write-Error "Rode: gh auth login" }
$GHCR_USER = $ghUserMatch.Groups[1].Value
if ($env:GHCR_PAT) { $GHCR_TOKEN = $env:GHCR_PAT.Trim() }
else { $GHCR_TOKEN = (gh auth token --hostname github.com).Trim() }
if (-not $GHCR_TOKEN) { Write-Error "Defina GHCR_PAT em ~/.claude/.env" }
$authB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${GHCR_USER}:${GHCR_TOKEN}"))
$dockerCfgDir = Join-Path $env:TEMP "aje-de-boxe-docker-config"
if (Test-Path $dockerCfgDir) { Remove-Item $dockerCfgDir -Recurse -Force }
New-Item -ItemType Directory -Path $dockerCfgDir | Out-Null
$cfgJson = @{ auths = @{ "ghcr.io" = @{ auth = $authB64 } } } | ConvertTo-Json -Depth 5 -Compress
[IO.File]::WriteAllBytes((Join-Path $dockerCfgDir "config.json"), [Text.UTF8Encoding]::new($false).GetBytes($cfgJson))
$env:DOCKER_CONFIG = $dockerCfgDir
Write-Host "Auth OK como $GHCR_USER" -ForegroundColor Green

Write-Host "=== [2/4] Build + Push ===" -ForegroundColor Cyan
$builderName = "aje-de-boxe-builder"
$buildxList  = docker buildx ls
if (-not ($buildxList | Select-String $builderName)) {
    docker buildx create --name $builderName --driver docker-container --use | Out-Null
} else {
    docker buildx use $builderName | Out-Null
}
$metaFile = Join-Path $env:TEMP "aje-de-boxe-meta.json"
docker buildx build --platform linux/amd64 --push --tag $IMAGE --metadata-file $metaFile $projectRoot
if ($LASTEXITCODE -ne 0) { Write-Error "Build falhou." }
$meta   = Get-Content $metaFile -Raw | ConvertFrom-Json
$DIGEST = $meta."containerimage.digest"
if (-not $DIGEST) { Write-Error "Nao foi possivel extrair digest." }
$IMAGE_REF = "${IMAGE}@${DIGEST}"
Write-Host "Digest: $DIGEST" -ForegroundColor Green

Write-Host "=== [3/4] Deploy via Portainer ===" -ForegroundColor Cyan
$baseUrl = $PORTAINER_URL.TrimEnd("/")
$headers = @{ "X-API-Key" = $PORTAINER_TOKEN; "Content-Type" = "application/json" }
foreach ($svcName in $SERVICES) {
    Write-Host "  Atualizando $svcName..."
    $svcResp = Invoke-RestMethod -Uri "$baseUrl/api/endpoints/1/docker/services/$svcName" -Headers $headers -Method Get
    $version = $svcResp.Version.Index
    $spec    = $svcResp.Spec | ConvertTo-Json -Depth 20 | ConvertFrom-Json
    $spec.TaskTemplate.ContainerSpec.Image = $IMAGE_REF
    $fu = if ($spec.TaskTemplate.PSObject.Properties["ForceUpdate"]) { $spec.TaskTemplate.ForceUpdate } else { 0 }
    $spec.TaskTemplate.ForceUpdate = $fu + 1
    $body = $spec | ConvertTo-Json -Depth 20
    Invoke-RestMethod -Uri "$baseUrl/api/endpoints/1/docker/services/$svcName/update?version=$version" -Headers $headers -Method Post -Body $body | Out-Null
    Write-Host "  OK: $svcName" -ForegroundColor Green
}

Write-Host "=== [4/4] Verificando $VERIFY_URL ===" -ForegroundColor Cyan
$ok = $false
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 4
    try { $code = (Invoke-WebRequest -Uri $VERIFY_URL -Method Get -TimeoutSec 5 -UseBasicParsing).StatusCode }
    catch { $code = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 } }
    Write-Host "[$i] HTTP $code"
    if ($code -ge 200 -and $code -lt 500) { $ok = $true; break }
}
if (-not $ok) { Write-Error "Servico nao respondeu em 2 minutos." }
Write-Host ""
Write-Host "Deploy concluido!" -ForegroundColor Green
Write-Host "  Imagem  : $IMAGE_REF"
Write-Host "  Servicos: $($SERVICES -join ', ')"
