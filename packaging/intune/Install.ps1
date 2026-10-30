$ErrorActionPreference = 'Stop'
try {
    $package = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package.json') -Raw | ConvertFrom-Json
    $msi = Join-Path $PSScriptRoot 'HandyNpu.msi'
    # .NET avoids Get-FileHash's script-module autoload dependency in Windows PowerShell.
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($msi)
    try { $hash = [System.BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','') }
    finally { $stream.Dispose(); $sha.Dispose() }
    if ($hash -ne $package.sha256) {
        throw 'Installer SHA256 mismatch'
    }
    $log = Join-Path $env:TEMP 'Handy-CoreUltra355-NPU-install.log'
    $msiArgs = "/i `"$msi`" /qn /norestart /L*v `"$log`" ALLUSERS=1 MSIINSTALLPERUSER=`"`""
    $process = Start-Process -FilePath "$env:SystemRoot\System32\msiexec.exe" -ArgumentList $msiArgs -WindowStyle Hidden -Wait -PassThru
    exit $process.ExitCode
} catch { Write-Error $_ -ErrorAction Continue; exit 1603 }
