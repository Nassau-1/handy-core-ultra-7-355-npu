"""Read-only Windows prerequisites before NPU compilation; no fallback device."""
import json
import os
import subprocess

MIN_DRIVER = (32, 0, 100, 5540)


def compatibility_error(info):
    if info.get('pending_boot') and info.get('pending_boot') == info.get('boot'):
        return 'Restart Windows to finish the Intel NPU driver update, then reopen Handy.'
    try:
        version = tuple(int(part) for part in info['driver'].split('.'))
    except (KeyError, AttributeError, ValueError):
        return 'Intel NPU driver missing or unreadable. Repair Handy from Company Portal.'
    if len(version) != 4 or version < MIN_DRIVER:
        return 'Intel NPU driver 32.0.100.5540 or newer is required. Repair Handy from Company Portal and restart Windows.'
    return None


def check_windows():
    if os.name != 'nt':
        return
    script = r'''
$ErrorActionPreference = 'Stop'
$driver = Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.Manufacturer -like '*Intel*' -and ($_.DeviceClass -eq 'COMPUTEACCELERATOR' -or $_.DeviceName -like '*AI Boost*') } | Select-Object -First 1
$boot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToUniversalTime().ToString('o')
$key = 'HKLM:\SOFTWARE\Nassau\HandyNpu'
$pending = (Get-ItemProperty -LiteralPath $key -Name PendingDriverBoot -ErrorAction SilentlyContinue).PendingDriverBoot
@{driver=$driver.DriverVersion; boot=$boot; pending_boot=$pending} | ConvertTo-Json -Compress
'''
    powershell = os.path.join(os.environ['SystemRoot'], 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    result = subprocess.run([powershell, '-NoProfile', '-NonInteractive', '-Command', script],
        check=True, capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    error = compatibility_error(json.loads(result.stdout))
    if error:
        raise RuntimeError(error)
