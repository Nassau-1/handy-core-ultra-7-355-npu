# Windows and Intune operations

The target catalog is **Intune Company Portal**. A custom Win32 app does not need
publication in the public Microsoft Store. Microsoft documents the required
[silent installer and .intunewin preparation](https://learn.microsoft.com/en-us/intune/app-management/deployment/create-win32-package)
and [Win32 settings](https://learn.microsoft.com/en-us/intune/app-management/deployment/add-win32).

## Build outputs

The Windows workflow produces MSI/EXE plus `handy-ultra355-intune` containing:
`Install.intunewin`, `Detect.ps1`, `Require-CoreUltra355.ps1`, `intune-metadata.json`.
The metadata contains the exact MSI ProductCode, version, install/uninstall commands
and package SHA256. Never invent or reuse a ProductCode from another release.

The package includes model, runtime and app. It does not install an Intel driver,
modify security policies or compile the model as SYSTEM. Compilation happens when
the user loads the model and writes only to their LocalAppData cache.

## Intune configuration

1. Apps > Windows > Add > Windows app (Win32); select `Install.intunewin`.
2. Display name `Handy Core Ultra 355 NPU (Preview)`, publisher `Nassau-1`.
3. Copy the exact commands from `intune-metadata.json`. Install behavior **System**;
   60-minute install limit, no forced reboot. Return 0 success, 3010 soft reboot,
   1618 retry; 1603 failure. Standard MSI error defaults apply.
4. Architecture x64. Require supported Windows 11 (target 25H2/build 26200+) and
   custom requirement `Require-CoreUltra355.ps1`: 64-bit, SYSTEM, string equals `True`.
5. Custom detection `Detect.ps1`: 64-bit; success requires exit 0 and stdout.
   Signature enforcement only if scripts have actually been signed.
6. The owner requested availability to **All Users** on 2026-10-30. Use
   **Available for enrolled devices**, with the CPU/OS requirement enforced.
   This is an optional Preview, not a Required/ESP deployment. Real-device
   acceptance is still pending and must be stated in the catalog description.

The requirement checks the CPU/OS, not driver readiness or measured NPU performance.
Verify Intel NPU driver, WebView2 and App Control acceptance on the pilot.

## Maintenance and rollback

Upstream self-update is disabled. Test future MSI upgrades, then configure Intune
supersedence/version detection from the new artifact. Uninstall using the exact
MSI ProductCode command in metadata. User history and cache remain unless the user
explicitly removes them. Upstream Handy has a separate identity and is unaffected.

Current tenant upload, assignment and standard-user install are unverified. CI
installation proves packaging behavior only, not successful tenant delivery.
