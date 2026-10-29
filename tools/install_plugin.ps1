[CmdletBinding(SupportsShouldProcess=$true)]
param()
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$pluginSource=Join-Path $projectRoot 'plugin\Akko_TAC75_HE.js'
if(-not(Test-Path -LiteralPath $pluginSource)){throw 'Plugin source is missing.'}
$documents=[Environment]::GetFolderPath('MyDocuments')
$pluginFolder=Join-Path $documents 'WhirlwindFX\Plugins'
$backupFolder=Join-Path $documents ('WhirlwindFX\TAC75-Backups\'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Write-Host 'Exit SignalRGB normally before installing. This script never writes keyboard firmware.'
if($PSCmdlet.ShouldProcess($pluginFolder,'Install TAC75 plugin and back up older versions')){
 New-Item -ItemType Directory -Path $pluginFolder -Force | Out-Null
 New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null
 foreach($fileName in @('Akko_TAC75_HE.js','Akko_TAC75_RAM1_USB.js','Akko_TAC75_RAM1_Bridge.js','Akko_TAC75_Network_Bridge.js')){
  $existing=Join-Path $pluginFolder $fileName
  if(Test-Path -LiteralPath $existing){
   $backup=Join-Path $backupFolder $fileName
   Copy-Item -LiteralPath $existing -Destination $backup
   if((Get-FileHash -LiteralPath $existing).Hash -ne (Get-FileHash -LiteralPath $backup).Hash){throw 'Backup verification failed.'}
  }
 }
 $destination=Join-Path $pluginFolder 'Akko_TAC75_HE.js'
 Copy-Item -LiteralPath $pluginSource -Destination $destination -Force
 if((Get-FileHash -LiteralPath $pluginSource).Hash -ne (Get-FileHash -LiteralPath $destination).Hash){throw 'Installed plugin verification failed.'}
 foreach($fileName in @('Akko_TAC75_RAM1_USB.js','Akko_TAC75_RAM1_Bridge.js','Akko_TAC75_Network_Bridge.js')){
  $existing=Join-Path $pluginFolder $fileName
  if(Test-Path -LiteralPath $existing){Remove-Item -LiteralPath $existing}
 }
 Write-Host "Installed: $destination"
 Write-Host "Backups: $backupFolder"
 Write-Host 'Restart SignalRGB and enable per-key lighting. Fixed 5 FPS.'
}
