$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $root "app.py"
$pyw = Join-Path (Split-Path -Parent $root) "venv\Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $pyw)) {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $pyw = $cmd.Source
    } else {
        Write-Host "pythonw.exe was not found. Install Python or edit this script." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
if (-not (Test-Path -LiteralPath $app)) {
    Write-Host "app.py was not found: $app" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
$lnk = Join-Path $root "SimpleCellSegmentation.lnk"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = '"' + $app + '"'
$s.WorkingDirectory = $root
$icon = Join-Path $root "assets\simplecellsegmentation.ico"
if (Test-Path -LiteralPath $icon) { $s.IconLocation = $icon }
$s.Description = "SimpleCellSegmentation - Cellpose + ImageJ"
$s.WindowStyle = 1
$s.Save()
Write-Host "Shortcut created: $lnk" -ForegroundColor Green
