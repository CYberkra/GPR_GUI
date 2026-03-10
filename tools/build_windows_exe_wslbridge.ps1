$ErrorActionPreference = 'Stop'

param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
  [string]$CorePath = '',
  [switch]$SkipDependencyInstall,
  [switch]$SkipBuild
)

$script = Join-Path $PSScriptRoot 'build_windows_exe.ps1'
if (!(Test-Path $script)) {
  throw "build_windows_exe.ps1 not found: $script"
}

$params = @{
  RepoRoot = $RepoRoot
}
if (-not [string]::IsNullOrWhiteSpace($CorePath)) { $params.CorePath = $CorePath }
if ($SkipDependencyInstall) { $params.SkipDependencyInstall = $true }
if ($SkipBuild) { $params.SkipBuild = $true }

& $script @params
