$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcherPath = Join-Path $root 'start_turksoil.ps1'
$password = $null
$confirmation = $null

function ConvertTo-PlainText([System.Security.SecureString]$Value) {
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Value)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

try {
    $securePassword = Read-Host 'Choose an admin password (16 characters minimum)' -AsSecureString
    $password = ConvertTo-PlainText $securePassword
    if ($password.Length -lt 16) {
        throw 'Choose a password with at least 16 characters.'
    }

    $secureConfirmation = Read-Host 'Enter the same password again' -AsSecureString
    $confirmation = ConvertTo-PlainText $secureConfirmation
    if (-not [string]::Equals($password, $confirmation, [StringComparison]::Ordinal)) {
        throw 'The passwords did not match. Nothing was saved.'
    }

    $listeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
    $processIds = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
    foreach ($processId in $processIds) {
        $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId"
        $processName = (Get-Process -Id $processId -ErrorAction Stop).ProcessName
        if ($processName -notmatch '^python(w)?$' -or $processInfo.CommandLine -notmatch 'server\.py') {
            throw 'Port 8000 is occupied by another application. Nothing was saved or stopped; close that application and run this setup again.'
        }
    }

    foreach ($processId in $processIds) {
        Stop-Process -Id $processId
    }

    if ($listeners.Count -gt 0) {
        Start-Sleep -Milliseconds 500
    }

    [Environment]::SetEnvironmentVariable('TURKSOIL_ADMIN_PASSWORD', $password, 'User')
    $env:TURKSOIL_ADMIN_PASSWORD = $password
    $env:PORT = '8000'
    $env:SITE_BASE_URL = 'http://localhost:8000'

    Write-Host 'Admin password saved to your Windows user environment. It was not written to the project files.'
    Write-Host 'Starting the local site with admin sign-in enabled.'
    & $launcherPath
} finally {
    Remove-Item Env:TURKSOIL_ADMIN_PASSWORD -ErrorAction SilentlyContinue
    $password = $null
    $confirmation = $null
    Remove-Variable securePassword, secureConfirmation -ErrorAction SilentlyContinue
}
