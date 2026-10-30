param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$build = Join-Path $repo 'build\intune'
$source = Join-Path $build 'source'
$output = Join-Path $build 'output'
New-Item -ItemType Directory -Force -Path $source,$output | Out-Null
$msi = (Resolve-Path -LiteralPath $Installer).Path
$wi = New-Object -ComObject WindowsInstaller.Installer
$db = $wi.OpenDatabase($msi,0)
function Get-MsiProperty([string]$Name) {
    $view = $db.OpenView("SELECT Value FROM Property WHERE Property = '$Name'")
    [void]$view.Execute()
    $value = $view.Fetch().StringData(1)
    [void]$view.Close()
    return $value
}
$code = Get-MsiProperty 'ProductCode'
$version = Get-MsiProperty 'ProductVersion'
$name = Get-MsiProperty 'ProductName'
if ($code -notmatch '^\{[A-F0-9-]{36}\}$' -or $name -ne 'Handy Core Ultra 355 NPU') { throw "Unexpected MSI identity: name=$name; code=$code" }
Copy-Item -LiteralPath $msi -Destination (Join-Path $source 'HandyNpu.msi')
Copy-Item -LiteralPath (Join-Path $repo 'packaging\intune\Install.ps1') -Destination $source
@{ productCode=$code; version=$version; sha256=(Get-FileHash -LiteralPath $msi -Algorithm SHA256).Hash } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $source 'package.json') -Encoding utf8
$detect = @'
$ErrorActionPreference = 'Stop'
try {
    $key = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PRODUCTCODE'
    $app = Get-ItemProperty -LiteralPath $key -ErrorAction Stop
    if ($app.DisplayName -eq 'Handy Core Ultra 355 NPU' -and [version]$app.DisplayVersion -ge [version]'APPVERSION') {
        Write-Output "Installed: $($app.DisplayVersion)"
        exit 0
    }
} catch {}
exit 1
'@
$detect.Replace('PRODUCTCODE',$code).Replace('APPVERSION',$version) |
    Set-Content -LiteralPath (Join-Path $output 'Detect.ps1') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $repo 'packaging\intune\Require-CoreUltra355.ps1') -Destination $output
$toolLock = Get-Content -LiteralPath (Join-Path $repo 'packaging\intune-tool-lock.json') -Raw | ConvertFrom-Json
$tool = Join-Path $build 'IntuneWinAppUtil.exe'
Invoke-WebRequest -Uri $toolLock.url -OutFile $tool
if ((Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash -ne $toolLock.sha256) { throw 'Content Prep Tool SHA256 mismatch' }
& $tool -c $source -s Install.ps1 -o $output -q
if ($LASTEXITCODE -ne 0) { throw "Intune packaging failed: $LASTEXITCODE" }
$metadata = @{
    name=$name; version=$version; productCode=$code; context='system';
    installCommand='%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File Install.ps1';
    uninstallCommand="msiexec.exe /x $code /qn /norestart";
    requirement='Require-CoreUltra355.ps1; 64-bit SYSTEM; string equals True';
    detection='Detect.ps1; 64-bit SYSTEM; success exit + nonempty stdout';
    assignments='None created by build; pilot Available only after hardware acceptance';
    packageSha256=(Get-FileHash -LiteralPath (Join-Path $output 'Install.intunewin') -Algorithm SHA256).Hash
}
$metadata | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $output 'intune-metadata.json') -Encoding utf8
Write-Output ($metadata | ConvertTo-Json)
