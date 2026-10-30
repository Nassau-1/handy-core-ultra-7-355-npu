# Intune custom requirement: string output equals True; run in 64-bit SYSTEM.
$ErrorActionPreference = 'Stop'
try {
    $cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
    $os = Get-CimInstance Win32_OperatingSystem
    $supported = [Environment]::Is64BitOperatingSystem -and
        [int]$os.BuildNumber -ge 26200 -and $os.ProductType -eq 1 -and
        $cpu -match 'Intel.*Core.*Ultra.*7\s+355\b'
    Write-Output ([string][bool]$supported)
    exit 0
} catch { Write-Output 'False'; exit 0 }
