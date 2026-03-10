$ErrorActionPreference = 'Stop'

param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
  [string]$CorePath = '',
  [string]$VenvName = '.venv_winbuild',
  [switch]$SkipDependencyInstall,
  [switch]$SkipBuild
)

function Test-PeMagic {
  param([Parameter(Mandatory = $true)][string]$Path)
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -lt 64) { return $false }
  if ($bytes[0] -ne 0x4D -or $bytes[1] -ne 0x5A) { return $false } # MZ
  $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
  if ($peOffset -lt 0 -or ($peOffset + 4) -ge $bytes.Length) { return $false }
  return ($bytes[$peOffset] -eq 0x50 -and $bytes[$peOffset + 1] -eq 0x45 -and $bytes[$peOffset + 2] -eq 0x00 -and $bytes[$peOffset + 3] -eq 0x00)
}

function Invoke-PeToolCheck {
  param([Parameter(Mandatory = $true)][string]$Path)

  $result = [ordered]@{
    method = 'none'
    output = ''
    passed = $false
  }

  if (Get-Command 7z -ErrorAction SilentlyContinue) {
    $out = (& 7z l $Path | Out-String)
    $result.method = '7z'
    $result.output = $out.Trim()
    $result.passed = ($out -match 'Type\s*=\s*PE')
    return $result
  }

  if (Get-Command objdump -ErrorAction SilentlyContinue) {
    $out = (& objdump -f $Path | Out-String)
    $result.method = 'objdump'
    $result.output = $out.Trim()
    $result.passed = ($out -match 'pei-i386|pei-x86-64|file format pe')
    return $result
  }

  if (Get-Command file -ErrorAction SilentlyContinue) {
    $out = (& file $Path | Out-String)
    $result.method = 'file'
    $result.output = $out.Trim()
    $result.passed = ($out -match 'PE32|PE32\+')
    return $result
  }

  return $result
}

if (-not (Test-Path $RepoRoot)) {
  throw "RepoRoot not found: $RepoRoot"
}

if ([string]::IsNullOrWhiteSpace($CorePath)) {
  $candidateCore = Join-Path (Split-Path $RepoRoot -Parent) 'PythonModule_core'
  if (Test-Path $candidateCore) {
    $CorePath = (Resolve-Path $candidateCore).Path
  }
}

if (-not (Test-Path $CorePath)) {
  throw "CorePath not found: $CorePath"
}

Set-Location $RepoRoot

$shortHash = (git rev-parse --short=7 HEAD).Trim()
$buildDate = Get-Date -Format 'yyyyMMdd'
$releaseBaseName = "GPR_GUI_Qt_win_${buildDate}_${shortHash}"
$releaseExeName = "$releaseBaseName.exe"

$py = Join-Path $RepoRoot "$VenvName\Scripts\python.exe"
if (!(Test-Path $py)) {
  py -3.10 -m venv $VenvName
  $py = Join-Path $RepoRoot "$VenvName\Scripts\python.exe"
}

if (-not $SkipDependencyInstall) {
  & $py -m pip install --upgrade pip
  & $py -m pip install pyinstaller PyQt6 numpy pandas matplotlib scipy
}

$hidden = @(
  'compensatingGain',
  'dewow',
  'set_zero_time',
  'agcGain',
  'subtracting_average_2D',
  'running_average_2D'
)

if (-not $SkipBuild) {
  $hargs = @()
  foreach($h in $hidden){ $hargs += @('--hidden-import', $h) }

  & $py -m PyInstaller --noconfirm --clean --onefile --windowed --name GPR_GUI_Qt `
    --paths $CorePath --add-data "assets;assets" --add-data "read_file_data.py;." @hargs app_qt.py
}

$distDir = Join-Path $RepoRoot 'dist'
$sourceExe = Join-Path $distDir 'GPR_GUI_Qt.exe'
if (!(Test-Path $sourceExe)) {
  throw "Build output not found: $sourceExe"
}

$releaseExe = Join-Path $distDir $releaseExeName
Copy-Item $sourceExe $releaseExe -Force

$releaseVersion = "win_${buildDate}_${shortHash}"
Set-Content -Path (Join-Path $distDir 'RELEASE_VERSION.txt') -Value $releaseVersion -Encoding utf8

$magicPassed = Test-PeMagic -Path $releaseExe
$toolCheck = Invoke-PeToolCheck -Path $releaseExe
$pePassed = $magicPassed -and ($toolCheck.method -eq 'none' -or $toolCheck.passed)

$verifyLog = Join-Path $distDir ($releaseBaseName + '_pe_verify.txt')
$verifyContent = @(
  "artifact=$releaseExe",
  "magic_check=$magicPassed",
  "tool_method=$($toolCheck.method)",
  "tool_check=$($toolCheck.passed)",
  "pe_verify_passed=$pePassed",
  "---- tool output ----",
  $toolCheck.output
) -join [Environment]::NewLine
Set-Content -Path $verifyLog -Value $verifyContent -Encoding utf8

if (-not $pePassed) {
  throw "PE verify failed. See: $verifyLog"
}

Write-Output "ARTIFACT=$releaseExe"
Write-Output "VERIFY_LOG=$verifyLog"
