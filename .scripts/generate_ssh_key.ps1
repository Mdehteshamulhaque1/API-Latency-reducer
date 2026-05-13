$sshDir = Join-Path $env:USERPROFILE '.ssh'
if (-not (Test-Path $sshDir)) {
  New-Item -ItemType Directory -Path $sshDir | Out-Null
  Write-Host 'Created .ssh directory'
} else {
  Write-Host '.ssh exists'
}

$keyBase = Join-Path $sshDir 'id_ed25519'
if (Test-Path $keyBase) {
  $timestamp = Get-Date -Format 'yyyyMMddHHmmss'
  $keyBase = Join-Path $sshDir ('id_ed25519_' + $timestamp)
}

ssh-keygen -t ed25519 -C 'hp@API-Latency-reducer' -f $keyBase -N '' -q

$svc = Get-Service -Name 'ssh-agent' -ErrorAction SilentlyContinue
if ($svc) {
  if ($svc.Status -ne 'Running') { Start-Service -Name 'ssh-agent' | Out-Null }
} else {
  Write-Host 'ssh-agent service not found; ensure OpenSSH client is installed'
}

ssh-add $keyBase | Out-Null

Write-Host '---PUBLIC KEY START---'
Get-Content ($keyBase + '.pub') | ForEach-Object { Write-Host $_ }
Write-Host '---PUBLIC KEY END---'
Write-Host 'Private key path:' $keyBase
