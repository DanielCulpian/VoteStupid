param(
    [ValidateSet('start', 'stop', 'status', 'logs')]
    [string]$Action = 'start'
)

$ErrorActionPreference = 'Stop'
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else {
    Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin/docker.exe'
}
if (-not (Test-Path -LiteralPath $dockerPath)) {
    throw 'No se encuentra Docker. Instala e inicia Docker Desktop.'
}

Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    # Local mode must never accidentally reuse an active public connector.
    if ($Action -in @('start', 'stop')) {
        & $dockerPath compose -f compose.yaml -f compose.tunnel.yaml stop cloudflared
        if ($LASTEXITCODE -ne 0) { throw 'No se ha podido detener el túnel antes de cambiar al modo local.' }
    }
    switch ($Action) {
        'start' { & $dockerPath compose up -d --build --wait --wait-timeout 180 }
        'stop' { & $dockerPath compose stop }
        'status' { & $dockerPath compose ps -a }
        'logs' { & $dockerPath compose logs --tail 100 -f }
    }
    if ($LASTEXITCODE -ne 0) { throw 'Docker no ha completado la operación. Revisa los mensajes anteriores.' }
    if ($Action -eq 'start') { Write-Host 'VoteStupid iniciado. Acceso predeterminado: http://localhost:8080' }
} finally {
    Pop-Location
}
