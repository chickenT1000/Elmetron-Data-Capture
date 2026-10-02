param(
  [Parameter(Mandatory=$true)][string]$Installer,
  [Parameter(Mandatory=$true)][string]$InstallDir,
  [Parameter(Mandatory=$true)][string]$DataDir
)
$ErrorActionPreference = 'Stop'
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$installPath = [IO.Path]::GetFullPath($InstallDir)
$dataPath = [IO.Path]::GetFullPath($DataDir)
if (Test-Path -LiteralPath $installPath) { throw 'Use a new disposable install directory' }
if (Test-Path -LiteralPath $dataPath) { throw 'Use a new disposable data directory' }
$argsList = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER', '/NOICONS', "/DIR=$installPath")
$process = Start-Process -FilePath $installerPath -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Install failed' }
$env:ELMETRON_DATA_DIR = $dataPath
# Only Windows system binaries on PATH: installed runtime must not need Python/Node.
$savedPath = $env:PATH
try {
  $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
  & "$installPath\elmetron-cli.exe" --data-dir $dataPath validate-config
  if ($LASTEXITCODE -ne 0) { throw 'Packaged CLI failed' }
  $stdout = Join-Path $dataPath 'server.stdout.log'
  $stderr = Join-Path $dataPath 'server.stderr.log'
  New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
  $server = Start-Process -FilePath "$installPath\elmetron-cli.exe" -ArgumentList @('--data-dir',$dataPath,'serve','--port','18050') -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  for ($i=0;$i -lt 120;$i++) {
    try { $health=Invoke-RestMethod 'http://127.0.0.1:18050/health'; break } catch { Start-Sleep -Milliseconds 250 }
  }
  if ($health.service -ne 'elmetron') { throw 'Packaged backend failed' }
  $token=(Get-Content -LiteralPath "$dataPath\config\api-token" -Raw).Trim()
  Invoke-RestMethod 'http://127.0.0.1:18050/api/v1/capture/start' -Method Post -ContentType 'application/json' -Body '{"demo":true}' -Headers @{Authorization="Bearer $token"} | Out-Null
  Start-Sleep -Seconds 8
  $status=Invoke-RestMethod 'http://127.0.0.1:18050/api/v1/live/status'
  if ($status.frames -lt 2 -or $status.mode -ne 'demo') { throw 'Packaged demo failed' }
  $blockedUpdate = Start-Process -FilePath $installerPath -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
  if ($blockedUpdate.ExitCode -eq 0) { throw 'Update must refuse while the backend is running' }
  $stillRunning = Invoke-RestMethod 'http://127.0.0.1:18050/api/v1/live/status'
  if ($stillRunning.state -ne 'running') { throw 'Blocked update interrupted capture' }
  Invoke-RestMethod 'http://127.0.0.1:18050/api/v1/server/shutdown' -Method Post -Headers @{Authorization="Bearer $token"} | Out-Null
  if (-not $server.WaitForExit(15000)) { throw 'Backend did not stop gracefully' }
} finally { $env:PATH=$savedPath; Remove-Item Env:ELMETRON_DATA_DIR -ErrorAction SilentlyContinue }
$db = Join-Path $dataPath 'demo\data\elmetron.sqlite'
$beforeDb = (Get-FileHash -LiteralPath $db).Hash
$config = Join-Path $dataPath 'config\app.toml'
Add-Content -LiteralPath $config -Value '# installer preservation sentinel'
$beforeConfig = (Get-FileHash -LiteralPath $config).Hash
$update = Start-Process -FilePath $installerPath -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if ($update.ExitCode -ne 0) { throw 'Update failed' }
if ((Get-FileHash -LiteralPath $db).Hash -ne $beforeDb) { throw 'Update changed data' }
if ((Get-FileHash -LiteralPath $config).Hash -ne $beforeConfig) { throw 'Update changed config' }
$uninstall = Start-Process -FilePath "$installPath\unins000.exe" -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -WindowStyle Hidden -Wait -PassThru
if ($uninstall.ExitCode -ne 0) { throw 'Uninstall failed' }
if ((Get-FileHash -LiteralPath $db).Hash -ne $beforeDb) { throw 'Uninstall changed data' }
if ((Get-FileHash -LiteralPath $config).Hash -ne $beforeConfig) { throw 'Uninstall changed config' }
Write-Output 'Install, demo without Python/Node PATH, running-update refusal, update and uninstall preservation passed.'
