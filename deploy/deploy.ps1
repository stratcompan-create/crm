<#
  Publica o CRM em produção: testes locais -> push -> backup -> build da imagem -> redeploy -> migração -> conferência.

  Antes de usar:
    - Docker Desktop aberto, com os containers crm-frappe-1, crm-mariadb-1 e crm-redis-1 de pé;
    - chave SSH do servidor (padrão: ~\.ssh\stratcompany_crm);
    - variável CRM_DEPLOY_HOST com o endereço do servidor.

  Uso:
    $env:CRM_DEPLOY_HOST = "endereco-do-servidor"
    .\deploy\deploy.ps1                 # roda tudo
    .\deploy\deploy.ps1 -SkipTests      # só em emergência
#>
param(
  [string]$DeployHost = $env:CRM_DEPLOY_HOST,
  [string]$Key = "$env:USERPROFILE\.ssh\stratcompany_crm",
  [string]$Site = "crm.stratcompany.com",
  [string]$LocalSite = "crm.localhost",
  [string]$LocalContainer = "crm-frappe-1",
  [string]$Branch = "develop",
  [string]$VerifyUrl = "",
  [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
if (-not $DeployHost) { throw "Defina CRM_DEPLOY_HOST (ou use -DeployHost)." }
if (-not (Test-Path $Key)) { throw "Chave SSH não encontrada em $Key" }

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Ssh($cmd) { & ssh -i $Key -o StrictHostKeyChecking=accept-new "root@$DeployHost" $cmd }

# 1. testes
if (-not $SkipTests) {
  Step "Testes de fumaça (ambiente local)"
  $log = docker exec -w /home/frappe/frappe-bench $LocalContainer bash -c "bench --site $LocalSite execute crm.tests.run_smoke.run_all 2>&1 | grep -E '^===|FAIL|RESULTADO|Traceback'"
  $log | ForEach-Object { Write-Host $_ }
  if (($log -match "FAIL|Traceback") -or -not ($log -match "RESULTADO GERAL")) { throw "Testes falharam. Nada foi publicado." }
}

# 2. push
Step "Enviando o código para o GitHub"
$commit = docker exec -w /home/frappe/frappe-bench/apps/crm $LocalContainer git rev-parse --short HEAD
$dirty = docker exec -w /home/frappe/frappe-bench/apps/crm $LocalContainer git status --porcelain
if ($dirty) { throw "Há alterações sem commit. Faça o commit antes de publicar." }
$push = docker exec -w /home/frappe/frappe-bench/apps/crm $LocalContainer git push upstream $Branch 2>&1 | Out-String
Write-Host ($push -replace 'https://[^@\s]+@', 'https://***@')

# 3. backup + build
Step "Backup do site e início do build da imagem"
Ssh "docker exec frappe-backend-1 bench --site $Site backup 2>&1 | tail -1"
Ssh "cd /root/frappe_docker && (nohup docker build --no-cache --build-arg=FRAPPE_BRANCH=version-15 --secret=id=apps_json,src=apps.json --tag=stratcompany-crm:custom --file=images/layered/Containerfile . > /root/build.log 2>&1 &); sleep 1; echo build iniciado"

Step "Aguardando o build (cerca de 7 minutos)"
$done = $false
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep 30
  $ok = Ssh "grep -c 'naming to' /root/build.log"
  if ("$ok".Trim() -eq "1") { $done = $true; break }
  $failed = Ssh "grep -c -E '^ERROR|failed to solve' /root/build.log"
  if ([int]("$failed".Trim()) -gt 0) { throw "O build falhou. Veja /root/build.log no servidor." }
}
if (-not $done) { throw "O build demorou demais." }

# 4. redeploy + migração
Step "Recriando os containers e migrando o banco"
Ssh "cd /root && docker compose -f /root/frappe-compose.yml --env-file /root/frappe.env -p frappe up -d --force-recreate 2>&1 | tail -1; sleep 30; docker exec frappe-backend-1 bench --site $Site migrate 2>&1 | tr '\r' '\n' | grep -v 'Updating DocTypes' | tail -2; docker exec frappe-backend-1 bench --site $Site clear-cache"

# 5. conferência
Step "Conferindo o site"
$login = curl.exe -s -o NUL -w "%{http_code}" "https://$Site/login"
Write-Host "login: $login"
if ($VerifyUrl) { Write-Host ("verificação extra: " + (curl.exe -s $VerifyUrl)) }
if ($login -ne "200") { throw "O login não respondeu 200 após o deploy." }
Write-Host "`nPublicado: commit $commit em https://$Site" -ForegroundColor Green
