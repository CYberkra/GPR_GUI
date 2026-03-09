$ErrorActionPreference = 'Stop'

# Stable Windows build script for GPR_GUI Qt app
$repo = 'E:\Openclaw\.openclaw\workspace\repos\GPR_GUI'
$core = 'E:\Openclaw\.openclaw\workspace\repos\PythonModule_core'
Set-Location $repo

$py = Join-Path $repo '.venv_winbuild\Scripts\python.exe'
if (!(Test-Path $py)) {
  py -3.10 -m venv .venv_winbuild
  $py = Join-Path $repo '.venv_winbuild\Scripts\python.exe'
}

& $py -m pip install --upgrade pip
& $py -m pip install pyinstaller PyQt6 numpy pandas matplotlib scipy

$hidden = @(
  'compensatingGain',
  'dewow',
  'set_zero_time',
  'agcGain',
  'subtracting_average_2D',
  'running_average_2D'
)

$hargs = @()
foreach($h in $hidden){ $hargs += @('--hidden-import', $h) }

& $py -m PyInstaller --noconfirm --clean --onefile --windowed --name GPR_GUI_Qt `
  --paths $core --add-data "assets;assets" --add-data "read_file_data.py;." @hargs app_qt.py

Write-Output (Join-Path $repo 'dist\GPR_GUI_Qt.exe')
