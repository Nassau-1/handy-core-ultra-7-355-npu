# Run only on a disposable CI Windows runner, never the authoring workstation.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This smoke test is restricted to disposable GitHub runners' }
$repo = Split-Path $PSScriptRoot -Parent
$meta = Get-Content (Join-Path $repo 'build/intune/output/intune-metadata.json') -Raw | ConvertFrom-Json
$key = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\$($meta.productCode)"
if (Test-Path -LiteralPath $key) { throw 'Test product already installed; refusing to alter an existing install' }
try {
    $script = Join-Path $repo 'build/intune/source/Install.ps1'
    $stdout = Join-Path $repo 'build/install-stdout.log'
    $stderr = Join-Path $repo 'build/install-stderr.log'
    $proc = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$script`"" -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    if ($proc.ExitCode -notin @(0,3010)) {
        Get-Content -LiteralPath $stdout,$stderr -ErrorAction SilentlyContinue | Write-Host
        $msiLog = Join-Path $env:TEMP 'Handy-CoreUltra355-NPU-install.log'
        if (Test-Path -LiteralPath $msiLog) {
            Copy-Item -LiteralPath $msiLog -Destination (Join-Path $repo 'build/msi-install.log')
            Select-String -LiteralPath $msiLog -Pattern 'Return value 3','Error ','error status' -Context 12,3 | Out-String | Write-Host
        }
        throw "Installation failed: $($proc.ExitCode)"
    }
    & (Join-Path $repo 'build/intune/output/Detect.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Intune detection failed after install' }
    $install = Join-Path $env:ProgramFiles 'Handy Core Ultra 355 NPU'
    if (-not (Test-Path -LiteralPath (Join-Path $install 'handy.exe'))) { throw 'Machine installation not found in Program Files' }
    # GUI-subsystem executables require an explicit wait before reading redirected stdout.
    $modelOut = Join-Path $repo 'build/models-stdout.log'
    $modelErr = Join-Path $repo 'build/models-stderr.log'
    $modelProcess = Start-Process -FilePath (Join-Path $install 'handy.exe') -ArgumentList '--list-models --json' -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $modelOut -RedirectStandardError $modelErr
    if ($modelProcess.ExitCode -ne 0) {
        Get-Content -LiteralPath $modelErr | Write-Host
        throw 'Installed app cannot enumerate models'
    }
    $model = @(Get-Content -LiteralPath $modelOut -Raw | ConvertFrom-Json) | Where-Object { $_.id -eq 'openvino-turbo-int8-npu' }
    if (@($model).Count -ne 1 -or -not $model.is_downloaded -or -not $model.is_recommended) { throw 'Installed app cannot resolve the bundled NPU model' }
    $npu = Join-Path $install 'resources/npu'
    $probe = & (Join-Path $npu 'worker/handy-npu-worker.exe') --probe
    if ($LASTEXITCODE -ne 0) { throw 'Installed NPU runtime cannot load' }
    $devices = ($probe | ConvertFrom-Json).devices
    if ('NPU' -notin $devices) {
        $output = & (Join-Path $npu 'worker/handy-npu-worker.exe') (Join-Path $npu 'model') (Join-Path $env:TEMP 'handy-npu-smoke-cache')
        $workerExitCode = $LASTEXITCODE
        $messages = @($output | ForEach-Object { $_ | ConvertFrom-Json })
        $failures = @($messages | Where-Object { $_.PSObject.Properties.Name -contains 'ready' })
        if ($workerExitCode -eq 0 -or $failures.Count -ne 1 -or $failures[0].ready -ne $false -or $failures[0].error -notmatch 'NPU') { throw 'Expected explicit NPU-unavailable failure' }
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
exit 0
