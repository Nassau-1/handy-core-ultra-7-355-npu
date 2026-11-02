$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../packaging/intune/NpuDriver.ps1')
foreach ($version in @('', 'invalid', '32.0.100.4509')) {
    if (Test-NpuDriverCurrent $version '32.0.100.5540') { throw "Invalid version accepted: $version" }
}
foreach ($version in @('32.0.100.5540', '32.0.100.6000', '33.0.1.1')) {
    if (-not (Test-NpuDriverCurrent $version '32.0.100.5540')) { throw "Current/newer version rejected: $version" }
}
foreach ($code in @(0,14,3010)) {
    if ((Convert-NpuExitCode $code) -ne 3010) { throw 'Missing soft reboot signal' }
}
foreach ($code in @(1,8,13,1000,1603)) {
    $failed = $false
    try { Convert-NpuExitCode $code | Out-Null } catch { $failed = $true }
    if (-not $failed) { throw "Installer failure swallowed: $code" }
}
Write-Output 'Driver version, no-downgrade and exit-code policy passed.'
