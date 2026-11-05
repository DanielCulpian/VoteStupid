param(
    [ValidateSet('start', 'stop', 'status', 'logs', 'url')]
    [string]$Action = 'start',
    [ValidateSet('named', 'temporary')]
    [string]$Mode = 'named',
    [string]$Hostname
)

$ErrorActionPreference = 'Stop'
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$dockerPath = if ($dockerCommand) { $dockerCommand.Source } else {
    Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin/docker.exe'
}
if (-not (Test-Path -LiteralPath $dockerPath)) { throw 'Inicia Docker Desktop antes de publicar.' }
$projectRoot = Split-Path $PSScriptRoot -Parent
$originFile = Join-Path $projectRoot '.env.tunnel'
$urlFile = Join-Path $projectRoot '.tunnel-url'
$namedMode = $Mode -eq 'named'

# Run Compose and abort on errors without displaying private configuration.
function Invoke-TunnelCompose {
    param([string[]]$Arguments)
    $files = @('-f', 'compose.yaml', '-f', 'compose.tunnel.yaml')
    if ($namedMode -and $Action -eq 'start') { $files += @('-f', 'compose.tunnel.named.yaml') }
    & $dockerPath compose --env-file .env --env-file .env.tunnel @files @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Ha fallado Docker Compose. Consulta los logs del túnel.' }
}

Push-Location $projectRoot
try {
    if ($Action -eq 'start') {
        if ($namedMode -and $Hostname -notmatch '^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[A-Za-z]{2,63}$') {
            throw 'Indica un hostname válido: .\scripts\tunnel.ps1 start -Hostname votestupid.tudominio.es'
        }
        $initialOrigin = if ($namedMode) { 'https://' + $Hostname.ToLowerInvariant() } else { 'https://unconfigured.invalid' }
        # Stop the previous link before creating another; never modify the private .env.
        if (-not (Test-Path -LiteralPath $originFile)) {
            Set-Content -LiteralPath $originFile -Value 'DOCKER_PUBLIC_ORIGIN=https://unconfigured.invalid' -Encoding ASCII
        }
        Invoke-TunnelCompose -Arguments @('stop', 'cloudflared')
        Set-Content -LiteralPath $originFile -Value "DOCKER_PUBLIC_ORIGIN=$initialOrigin" -Encoding ASCII
        try {
            Invoke-TunnelCompose -Arguments @('up', '-d', '--build', '--wait', '--wait-timeout', '180', 'db', 'backend', 'frontend')
            Invoke-TunnelCompose -Arguments @('up', '-d', '--no-deps', '--force-recreate', 'cloudflared')
            $publicUrl = if ($namedMode) { $initialOrigin } else { $null }
            $deadline = (Get-Date).AddSeconds(90)
            $connected = $false
            while (-not $connected -and (Get-Date) -lt $deadline) {
                $output = (& $dockerPath compose --env-file .env --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml logs --no-color cloudflared 2>&1 | Out-String)
                $found = [regex]::Match($output, 'https://[a-z0-9-]+\.trycloudflare\.com\b')
                if (-not $namedMode -and $found.Success) { $publicUrl = $found.Value }
                $connected = $publicUrl -and $output -match 'Registered tunnel connection'
                if ($connected) { break }
                Start-Sleep -Seconds 2
            }
            if (-not $connected) { throw 'Cloudflare no ha confirmado la conexión en 90 segundos.' }
            Set-Content -LiteralPath $originFile -Value "DOCKER_PUBLIC_ORIGIN=$publicUrl" -Encoding ASCII
            Invoke-TunnelCompose -Arguments @('up', '-d', '--wait', '--wait-timeout', '180', 'backend')
            Set-Content -LiteralPath $urlFile -Value $publicUrl -Encoding ASCII
            Write-Host "Dirección pública configurada: $publicUrl"
            Write-Host 'Comprueba status/logs y abre el enlace para confirmar la conexión con Cloudflare.'
            Write-Host "Administración: $publicUrl/acceso"
            Write-Host 'Para desconectarlo: .\scripts\tunnel.ps1 stop'
        } catch {
            # Do not leave the application published after an incomplete startup.
            & $dockerPath compose --env-file .env --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml stop cloudflared
            throw
        }
    } elseif ($Action -eq 'url') {
        if (-not (Test-Path -LiteralPath $urlFile)) { throw 'Todavía no se ha generado un enlace público.' }
        Get-Content -LiteralPath $urlFile
    } elseif (Test-Path -LiteralPath $originFile) {
        switch ($Action) {
            'stop' {
                Invoke-TunnelCompose -Arguments @('stop', 'cloudflared')
                Invoke-TunnelCompose -Arguments @('stop', 'frontend', 'backend', 'db')
                Write-Host 'Túnel y aplicación detenidos. Los datos se conservan.'
            }
            'status' { Invoke-TunnelCompose -Arguments @('ps', '-a') }
            'logs' { Invoke-TunnelCompose -Arguments @('logs', '--tail', '100', '-f', 'cloudflared') }
        }
    } else {
        Write-Host 'No hay una configuración de túnel creada en este proyecto.'
    }
} finally {
    Pop-Location
}
