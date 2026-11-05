param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$serverPath = Join-Path $root 'server.py'
$port = 8000
$startedServer = $false
$serverProcess = $null
$stdoutLog = Join-Path $env:TEMP "turksoil-server-$PID.out.log"
$stderrLog = Join-Path $env:TEMP "turksoil-server-$PID.err.log"

try {
    if ($env:PORT) {
        $parsedPort = 0
        if (-not [int]::TryParse($env:PORT, [ref]$parsedPort) -or $parsedPort -lt 1 -or $parsedPort -gt 65535) {
            throw 'PORT must be a valid TCP port between 1 and 65535.'
        }
        $port = $parsedPort
    }

    $siteUrl = "http://localhost:$port"
    $healthUrl = "http://127.0.0.1:$port"
    $env:PORT = [string]$port
    $env:SITE_BASE_URL = $siteUrl

    function Test-TurksoilServer {
        try {
            $page = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -Proxy $null -TimeoutSec 5
            if ($page.StatusCode -ne 200 -or $page.Content -notmatch '<title>TURKSOIL LIMITED</title>') {
                return $false
            }
            $status = Invoke-RestMethod -Uri "$healthUrl/api/payment-status" -Proxy $null -TimeoutSec 5
            return $null -ne $status.PSObject.Properties['ready']
        } catch {
            return $false
        }
    }

    if (Test-TurksoilServer) {
        if ($CheckOnly) {
            Write-Host "Turksoil is already running and healthy at $siteUrl. The existing server was left running."
            exit 0
        }
        Write-Host "Turksoil is already running at $siteUrl."
        Start-Process $siteUrl
        Write-Host 'The existing server was left running. Close this window when finished.'
        Read-Host 'Press Enter to close this launcher'
        exit 0
    }

    if ($env:TURKSOIL_ENABLE_STRIPE -eq '1') {
        if (-not $env:STRIPE_SECRET_KEY -or $env:STRIPE_SECRET_KEY -notlike 'sk_test_*') {
            throw 'Local launcher checkout is test-mode only. Set a Stripe sk_test_ key, or unset TURKSOIL_ENABLE_STRIPE.'
        }
        Write-Host 'Stripe test mode is enabled. No live Stripe key is permitted by this launcher.'
    } else {
        Remove-Item Env:STRIPE_SECRET_KEY -ErrorAction SilentlyContinue
        Remove-Item Env:STRIPE_WEBHOOK_SECRET -ErrorAction SilentlyContinue
        Write-Host 'Checkout is disabled for this local session. Set TURKSOIL_ENABLE_STRIPE=1 with an sk_test_ key to opt in.'
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $serverProcess = Start-Process -FilePath $python.Source -ArgumentList @('-u', "`"$serverPath`"") -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    } else {
        $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
        if (-not $pythonLauncher) {
            throw 'Python 3 was not found. Install Python 3 and enable the python or py command, then run this launcher again.'
        }
        $serverProcess = Start-Process -FilePath $pythonLauncher.Source -ArgumentList @('-3', '-u', "`"$serverPath`"") -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
    }
    $startedServer = $true

    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if ($serverProcess.HasExited) {
            $details = ''
            if (Test-Path -LiteralPath $stderrLog) {
                $details = (Get-Content -LiteralPath $stderrLog -Raw).Trim()
            }
            if (-not $details -and (Test-Path -LiteralPath $stdoutLog)) {
                $details = (Get-Content -LiteralPath $stdoutLog -Raw).Trim()
            }
            throw "The local server stopped before it became ready. $details"
        }
        if (Test-TurksoilServer) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) {
        throw "The local server did not become ready at $siteUrl. Check whether the port is already in use."
    }

    if ($CheckOnly) {
        Write-Host "Unified Turksoil system is ready at $siteUrl."
        exit 0
    }

    Start-Process $siteUrl
    Write-Host "Unified Turksoil system opened at $siteUrl."
    Write-Host 'The spaceship, mapping, services, and local contract server are available from this page.'
    Read-Host 'Press Enter to stop the server and close this launcher'
} catch {
    Write-Error $_
    exit 1
} finally {
    if ($startedServer -and $serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id
        try {
            $serverProcess.WaitForExit(5000)
        } catch {
            Write-Warning "Could not confirm shutdown for local server process $($serverProcess.Id)."
        }
    }
    foreach ($logPath in @($stdoutLog, $stderrLog)) {
        if (Test-Path -LiteralPath $logPath) {
            Remove-Item -LiteralPath $logPath -ErrorAction SilentlyContinue
        }
    }
}
