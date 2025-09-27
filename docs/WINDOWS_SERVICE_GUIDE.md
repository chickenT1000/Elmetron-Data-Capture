# Windows Service Deployment Guide

## Overview
`elmetron.service.windows_service` packages the capture supervisor so it can run in the background without an interactive console. Install it as a Windows service on lab workstations that require continuous logging.

## Requirements
- Python 3.10+ installed system-wide and added to `PATH`.
- Project repository staged at `C:\Elmetron` or another stable path (avoid user profiles for service accounts).
- FTDI D2XX drivers installed.
- Configuration files (`config/app.toml`, `config/protocols.toml`) tailored to the workstation.
- Default export templates in `config/templates/` kept alongside the configuration so the service account can render PDFs/XML without additional paths.
- Optional: `pywin32` (`pip install pywin32`) if using the native Windows service helper.

## Service Account Preparation
Deploy the service under a dedicated account so USB access and file permissions can be controlled explicitly.

1. Create a local user (example):
   ```powershell
   net user elmetron_svc "StrongPassword!123" /add
   net localgroup "Users" elmetron_svc /add
   ```
   For domain environments, provision a domain account instead and ensure it can log on to the target workstation.
2. Grant **Log on as a service**:
   - Group Policy: `secpol.msc › Local Policies › User Rights Assignment`.
   - Or via command line (requires Microsoft `ntrights.exe`):
     ```powershell
     ntrights -u elmetron_svc +r SeServiceLogonRight
     ```
3. Grant folder access to captures, exports, and logs:
   ```powershell
   $paths = 'C:\Elmetron', 'C:\Elmetron\captures', 'C:\Elmetron\exports', 'C:\Elmetron\logs'
   foreach ($p in $paths) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null } }
   icacls $paths /grant "elmetron_svc:(OI)(CI)(M)"
   ```
4. Allow USB access. If the meter requires administrator access, add the account to `Power Users` or create a local security policy granting **Load and unload device drivers**.
5. Deny interactive logon if required by policy (`Deny log on locally`) while leaving service logon intact.

## Log Retention & Monitoring
### Scheduling Built-in Log Rotation

Use the bundled script once it is copied to your deployment path:
```powershell
Copy-Item scripts/rotate_logs.ps1 C:/Elmetron/scripts/rotate_logs.ps1 -Force
schtasks /create /sc daily /st 02:00 /ru elmetron_svc /rp *** /tn "ElmetronLogRotate" /tr "PowerShell.exe -NoProfile -ExecutionPolicy Bypass -File C:/Elmetron/scripts/rotate_logs.ps1"
```
Adjust `/ru` and `/rp` to match the account that runs the capture service (use `/ru SYSTEM` when policy permits). Ensure Task Scheduler has "Run with highest privileges" enabled when USB access requires administrator rights.

- Direct NSSM stdout/stderr or `--health-log` output to `C:\Elmetron\logs\capture.log`. Rotate logs to keep 30 days of history.
- The repository ships `scripts/rotate_logs.ps1`; copy it to `C:\Elmetron\scripts\` (or point the scheduled task at the repo checkout) before registering the rotation job.
- Configure `[monitoring]` in `config/app.toml` (set `log_rotation_task = "ElmetronLogRotate"`) so the health API reports scheduled-task status.
- The `/health` endpoint includes a `log_rotation` object (`status` of ok/missing/stale/failed) for dashboards and remote monitoring.
- Recommended rotation task (daily at 02:00):
  ```powershell
  schtasks /create /sc daily /st 02:00 /tn "ElmetronLogRotate" /tr "PowerShell.exe -NoProfile -File C:\Elmetron\scripts\rotate_logs.ps1"
  ```
  With `rotate_logs.ps1` similar to:
  ```powershell
  $logDir = 'C:\Elmetron\logs'
  Get-ChildItem $logDir -Filter '*.log*' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item
  Compress-Archive -Path "$logDir\capture.log" -DestinationPath "$logDir\capture_$(Get-Date -Format yyyyMMdd).log.zip"
  Clear-Content "$logDir\capture.log"
  ```
- Ensure the service account has modify rights on the log directory; security teams can ingest logs via existing SIEM agents.
- Review SQLite sessions (`data/elmetron.sqlite`) weekly and archive or purge via the exporter tooling if storage is limited.

## Option A: Deploy with NSSM
1. Download NSSM (Non-Sucking Service Manager) and place `nssm.exe` in `C:\Tools`.
2. From an elevated PowerShell prompt:
   ```powershell
   C:\Tools\nssm.exe install ElmetronCapture "C:\Python311\python.exe" "C:\Elmetron\elmetron\service\windows_service.py" --config C:\Elmetron\config\app.toml --protocols C:\Elmetron\config\protocols.toml --watchdog-timeout 30 --health-api-port 8050 --health-log
   ```
3. Set the working directory to `C:\Elmetron` inside the NSSM UI.
4. Configure the service to restart on failure and run under `elmetron_svc` (or your designated service account).
5. Redirect stdout/stderr to `C:\Elmetron\logs\capture.log` and enable rotation under the **I/O** tab.
6. Start the service via `Start-Service ElmetronCapture`.

## Option B: PyWin32 Service Wrapper
1. Install `pywin32`: `python -m pip install pywin32`.
2. Register the service:
   ```powershell
   python elmetron\service\windows_service.py install --config config/app.toml --protocols config/protocols.toml --watchdog-timeout 30 --health-api-port 8050 --health-log --user .\elmetron_svc --password StrongPassword!123
   ```
3. Start it with `python elmetron\service\windows_service.py start`.
4. Use `stop`/`remove` subcommands to manage lifecycle.
5. Update Windows Services › Log On tab to switch the account if prompts change.

## Service Management
- Logs: confirm `--health-log` or redirected output writes to `C:\Elmetron\logs`. Combine with the rotation script above.
- Configuration changes require service restart. Keep backup copies of TOML files under version control.
- Use `python cx505_capture_service.py --list-devices` before installing to confirm the device index.
- For scheduled command changes, re-run `python trigger_calibration.py` manually; services no longer auto-fire calibrations.

## Troubleshooting
- **Service will not start**: verify the working directory and ensure the service account has required permissions (Log on as service, access to paths/USB).
- **Access denied to USB**: run the service under a user with local admin or grant `Load and unload device drivers` privilege and reconnect the CX-505.
- **No health endpoint**: ensure `--health-api-port` is not blocked by Windows Firewall; add an inbound rule if necessary.
- **Stale protocol profiles**: rerun `python validate_protocols.py config/protocols.toml` after edits and restart the service.
- **Logs stop rotating**: confirm the scheduled task runs under the same service account (or SYSTEM) and that the archive script has permission to write ZIP files.


