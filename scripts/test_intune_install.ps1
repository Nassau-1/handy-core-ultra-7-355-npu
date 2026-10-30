# Run only on a disposable CI Windows runner, never the authoring workstation.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This smoke test is restricted to disposable GitHub runners' }
$repo = Split-Path $PSScriptRoot -Parent
$meta = Get-Content (Join-Path $repo 'build/intune/output/intune-metadata.json') -Raw | ConvertFrom-Json
$key = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$($meta.productCode)"
if (Test-Path -LiteralPath $key) { throw 'Test product already installed; refusing to alter an existing install' }
try {
    $script = Join-Path $repo 'build/intune/source/Install.ps1'
    $proc = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" -WindowStyle Hidden -Wait -PassThru
    if ($proc.ExitCode -notin @(0,3010)) { throw "Installation failed: $($proc.ExitCode)" }
    & (Join-Path $repo 'build/intune/output/Detect.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Intune detection failed after install' }
    $install = Join-Path $env:ProgramFiles 'Handy Core Ultra 355 NPU'
    if (-not (Test-Path -LiteralPath (Join-Path $install 'handy.exe'))) { throw 'Machine installation not found in Program Files' }
    $npu = Join-Path $install 'resources/npu'
    $probe = & (Join-Path $npu 'worker/handy-npu-worker.exe') --probe
    if ($LASTEXITCODE -ne 0) { throw 'Installed NPU runtime cannot load' }
    $devices = ($probe | ConvertFrom-Json).devices
    if ('NPU' -notin $devices) {
        $output = & (Join-Path $npu 'worker/handy-npu-worker.exe') (Join-Path $npu 'model') (Join-Path $env:TEMP 'handy-npu-smoke-cache')
        $failure = $output | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -or $failure.ready -ne $false -or $failure.error -notmatch 'NPU') { throw 'Expected explicit NPU-unavailable failure' }
    }
    $inventory = Get-Content (Join-Path $npu 'inventory.json') -Raw | ConvertFrom-Json
    foreach ($entry in $inventory) {
        $path = Join-Path $npu $entry.path
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Installed payload mismatch: $($entry.path)" }
    }
    Write-Output 'Machine install, detection, runtime import, no-NPU error and complete payload hashes verified.'
} finally {
    $proc = Start-Process msiexec.exe -ArgumentList "/x $($meta.productCode) /qn /norestart" -WindowStyle Hidden -Wait -PassThru
    if ($proc.ExitCode -notin @(0,1605,3010)) { throw "Uninstall failed: $($proc.ExitCode)" }
}
if (Test-Path -LiteralPath $key) { throw 'Uninstall left the product registration' }
Write-Output 'Machine uninstall verified.'
