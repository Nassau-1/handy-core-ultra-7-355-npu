# Dot-sourced by Install.ps1. No downloads or modifications occur on import.
function Test-NpuDriverCurrent([string]$Installed, [string]$Minimum) {
    if ([string]::IsNullOrWhiteSpace($Installed)) { return $false }
    try { return ([version]$Installed -ge [version]$Minimum) } catch { return $false }
}

function Convert-NpuExitCode([int]$Code) {
    if ($Code -in @(0,14,3010)) { return 3010 }
    throw "Intel NPU installation failed (exit $Code). See C:\ProgramData\Intel\NPUInstaller."
}

function Get-NpuDriverVersion {
    $driver = Get-CimInstance Win32_PnPSignedDriver |
        Where-Object { $_.Manufacturer -like '*Intel*' -and ($_.DeviceClass -eq 'COMPUTEACCELERATOR' -or $_.DeviceName -like '*AI Boost*') } | Select-Object -First 1
    return $driver.DriverVersion
}

function Install-NpuPrerequisite([string]$Source) {
    $lock = Get-Content -LiteralPath (Join-Path $Source 'intel-driver-lock.json') -Raw | ConvertFrom-Json
    if (Test-NpuDriverCurrent (Get-NpuDriverVersion) $lock.version) { return 0 }
    $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
    if ($cpu -notmatch 'Intel.*Core.*Ultra\s+7\s+355(?:\s|$)') { throw 'This package is validated only for Intel Core Ultra 7 355.' }
    $installer = Join-Path $Source $lock.filename
    if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $lock.sha256) { throw 'Intel NPU installer SHA256 mismatch' }
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Intel Corporation(,|$)') {
        throw 'Intel NPU installer signature is not valid for Intel Corporation'
    }
    # Keep compilation blocked for this boot even if a later MSI action fails.
    $key = 'HKLM:\SOFTWARE\Nassau\HandyNpu'
    $boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -LiteralPath $key -Name PendingDriverBoot -Value $boot -PropertyType String -Force | Out-Null
    $process = Start-Process -FilePath $installer -ArgumentList $lock.arguments -WindowStyle Hidden -Wait -PassThru
    $result = Convert-NpuExitCode $process.ExitCode
    # The active CIM driver may still report its previous version until reboot.
    # Never force a restart or silently reinterpret an unknown failure as success.
    return $result
}
