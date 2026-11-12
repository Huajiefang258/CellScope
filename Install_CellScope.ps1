param(
    [string]$InstallDir = "",
    [switch]$Unattended,
    [string]$Models = "1",
    [switch]$NoImageJ,
    [switch]$NoDesktopShortcut,
    [switch]$SkipPip,
    [switch]$UseSystemSite
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Source = $PSScriptRoot
$Temp = Join-Path $env:TEMP ("CellScope_install_" + [Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $Temp -Force | Out-Null

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "== $Text" -ForegroundColor Cyan
}
function Write-Ok([string]$Text) { Write-Host "[完成] $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host "[提示] $Text" -ForegroundColor Yellow }
function Fail([string]$Text) {
    Write-Host ""
    Write-Host "[错误] $Text" -ForegroundColor Red
    Write-Host "安装未完成。可以检查网络/权限后重新运行安装程序。"
    exit 1
}

function Download-File([string]$Url, [string]$Dest) {
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("User-Agent", "Mozilla/5.0")
        $wc.DownloadFile($Url, $Dest)
        $wc.Dispose()
    } catch {
        Fail "下载失败：$Url`n$($_.Exception.Message)"
    }
}

function Find-Python {
    $specs = @(
        @("py", "-3.10"),
        @("py", "-3.11"),
        @("py", "-3.12"),
        @("python", $null),
        @("python3", $null)
    )
    foreach ($spec in $specs) {
        $exe = $spec[0]
        $arg = $spec[1]
        try {
            if ($arg) {
                $out = & $exe $arg -c "import sys; print(sys.executable)" 2>$null
            } else {
                $out = & $exe -c "import sys; print(sys.executable)" 2>$null
            }
            if ($LASTEXITCODE -ne 0 -or -not $out) { continue }
            $path = ($out | Select-Object -Last 1).ToString().Trim()
            if (-not (Test-Path -LiteralPath $path)) { continue }
            $ver = (& $path -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null | Select-Object -Last 1).ToString().Trim()
            if ($ver -match '^3\.(10|11|12)$') { return $path }
        } catch { }
    }
    return $null
}

function New-Shortcut([string]$Path, [string]$Target, [string]$Arguments, [string]$WorkingDir, [string]$Icon) {
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($Path)
    $sc.TargetPath = $Target
    $sc.Arguments = $Arguments
    $sc.WorkingDirectory = $WorkingDir
    if ($Icon -and (Test-Path -LiteralPath $Icon)) { $sc.IconLocation = $Icon }
    $sc.WindowStyle = 1
    $sc.Save()
}

$modelOptions = @(
    @{ Key = "cyto3";   Label = "cyto3（推荐，约 26 MB）" },
    @{ Key = "cyto2";   Label = "cyto2（约 26 MB）" },
    @{ Key = "cyto";    Label = "cyto（约 26 MB）" },
    @{ Key = "nuclei";  Label = "nuclei 细胞核（约 26 MB）" },
    @{ Key = "cpsam_v2"; Label = "Cellpose-SAM v2（约 1.2 GB，CPU 较慢）" },
    @{ Key = "cpsam";   Label = "Cellpose-SAM v1（约 1.2 GB，CPU 较慢）" }
)

Write-Host ""
Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host "  CellScope 安装程序" -ForegroundColor White
Write-Host "  Cellpose + ImageJ 细胞计数" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host "安装到当前用户目录，不需要管理员权限。"
Write-Host "需要网络连接；首次依赖安装可能需要 10–30 分钟。"

if (-not $Unattended) {
    $defaultDir = Join-Path $env:LOCALAPPDATA "CellScope"
    $inputDir = Read-Host "安装目录（直接回车 = $defaultDir）"
    if ([string]::IsNullOrWhiteSpace($inputDir)) { $InstallDir = $defaultDir }
    else { $InstallDir = $inputDir }
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "CellScope"
}
$InstallDir = [Environment]::ExpandEnvironmentVariables($InstallDir.Trim().Trim('"'))
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
if ($InstallDir -eq [IO.Path]::GetPathRoot($InstallDir)) { Fail "安装目录不能是磁盘根目录。" }

if (-not $Unattended) {
    Write-Host ""
    Write-Host "可选模型（可以稍后在界面中下载）："
    for ($i = 0; $i -lt $modelOptions.Count; $i++) {
        Write-Host ("  {0}) {1}" -f ($i + 1), $modelOptions[$i].Label)
    }
    Write-Host "  0) 不下载模型"
    $selection = Read-Host "请选择模型编号，逗号分隔（直接回车 = 1，输入 0 = 不下载）"
    if ([string]::IsNullOrWhiteSpace($selection)) { $Models = "1" }
    else { $Models = $selection }
    $ans = Read-Host "是否安装 ImageJ 1.54g？[Y/n]"
    if ($ans -match '^[nN]') { $NoImageJ = $true }
    $ans = Read-Host "是否创建桌面快捷方式？[Y/n]"
    if ($ans -match '^[nN]') { $NoDesktopShortcut = $true }
}

$selectedModels = @()
if (-not [string]::IsNullOrWhiteSpace($Models) -and $Models.Trim() -ne "0") {
    foreach ($piece in ($Models -split '[,，\s]+')) {
        if ($piece -match '^\d+$') {
            $idx = [int]$piece
            if ($idx -ge 1 -and $idx -le $modelOptions.Count) {
                $selectedModels += $modelOptions[$idx - 1].Key
            }
        }
    }
}
$selectedModels = @($selectedModels | Select-Object -Unique)
if ($selectedModels.Count -eq 0) { $selectedModels = @() }

Write-Host ""
Write-Host "安装位置：$InstallDir"
Write-Host ("模型：" + $(if ($selectedModels.Count) { $selectedModels -join ", " } else { "不下载" }))
Write-Host ("ImageJ：" + $(if ($NoImageJ) { "不安装" } else { "安装到 " + (Join-Path $InstallDir "ImageJ") }))
if (-not $Unattended) {
    $go = Read-Host "开始安装？[Y/n]"
    if ($go -match '^[nN]') { Write-Host "已取消。"; exit 0 }
}

# ---------------------------------------------------------------- copy app
Write-Step "1/6 复制程序文件"
$App = Join-Path $InstallDir "App"
New-Item -ItemType Directory -Path $App -Force | Out-Null
$files = @(
    "app.py", "cellpose_worker.py", "download_model.py", "requirements.txt",
    "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md",
    "Start_CellScope.bat", "Run_Debug.bat", "Create_Shortcut.bat",
    "Create_Shortcut.ps1", "Install_Dependencies.bat"
)
foreach ($name in $files) {
    $src = Join-Path $Source $name
    if (Test-Path -LiteralPath $src) {
        Copy-Item -LiteralPath $src -Destination $App -Force
    }
}
foreach ($dir in @("cellcounter", "vendor", "assets", "docs")) {
    $src = Join-Path $Source $dir
    if (-not (Test-Path -LiteralPath $src)) {
        if ($dir -eq "docs") { continue }
        Fail "安装包缺少目录：$dir"
    }
    Copy-Item -LiteralPath $src -Destination $App -Recurse -Force
}
Write-Ok "程序已复制到 $App"

# ---------------------------------------------------------------- python
Write-Step "2/6 检查 Python"
$py = Find-Python
if (-not $py) {
    Write-Warn "没有找到 Python 3.10–3.12，正在下载并安装 Python 3.10.11…"
    $pyInstaller = Join-Path $Temp "python-3.10.11-amd64.exe"
    Download-File "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe" $pyInstaller
    $pyDir = Join-Path $InstallDir "Python310"
    $args = "/quiet InstallAllUsers=0 PrependPath=0 Include_pip=1 Include_launcher=1 SimpleInstall=1 TargetDir=`"$pyDir`""
    $p = Start-Process -FilePath $pyInstaller -ArgumentList $args -Wait -PassThru
    $py = Join-Path $pyDir "python.exe"
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $py)) {
        Fail "Python 自动安装失败。请手动安装 Python 3.10 后重新运行安装程序。"
    }
}
Write-Ok "Python：$py"

$Venv = Join-Path $InstallDir "venv"
$venvPython = Join-Path $Venv "Scripts\python.exe"
$venvPythonw = Join-Path $Venv "Scripts\pythonw.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "创建独立 Python 环境…"
    $venvArgs = @("-m", "venv")
    if ($UseSystemSite) { $venvArgs += "--system-site-packages" }
    $venvArgs += $Venv
    & $py @venvArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        Fail "创建 Python 虚拟环境失败。"
    }
}
Write-Ok "Python 环境：$Venv"

# ---------------------------------------------------------------- deps
if (-not $SkipPip) {
    Write-Step "3/6 安装 Python 依赖"
    Write-Host "首次安装会下载 PyTorch / PyQt5 等组件，可能需要 10–30 分钟。"
    Write-Host "请保持网络连接，不要关闭此窗口。"
    & $venvPython -m pip install --upgrade pip --disable-pip-version-check
    & $venvPython -m pip install -r (Join-Path $App "requirements.txt") --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Fail "Python 依赖安装失败。请检查网络后重新运行安装程序。"
    }
    Write-Ok "依赖安装完成"
} else {
    Write-Step "3/6 跳过 Python 依赖（测试模式）"
}

# ---------------------------------------------------------------- imagej
Write-Step "4/6 安装 ImageJ"
$ImageJDir = Join-Path $InstallDir "ImageJ"
if ($NoImageJ) {
    Write-Warn "已跳过 ImageJ。程序会在程序目录或上一级目录的 ImageJ 中查找，或使用 IMAGEJ_HOME。"
} elseif ((Test-Path -LiteralPath (Join-Path $ImageJDir "ij.jar")) -and
          (Test-Path -LiteralPath (Join-Path $ImageJDir "jre\bin\java.exe"))) {
    Write-Ok "ImageJ 已存在"
} else {
    Write-Host "下载 ImageJ 1.54g（约 50 MB）…"
    $ijZip = Join-Path $Temp "ij154-win-java8.zip"
    Download-File "https://wsr.imagej.net/distros/win/ij154-win-java8.zip" $ijZip
    $ijExtract = Join-Path $Temp "ij_extract"
    Expand-Archive -LiteralPath $ijZip -DestinationPath $ijExtract -Force
    $ijJar = Get-ChildItem -Path $ijExtract -Recurse -Filter "ij.jar" -File | Select-Object -First 1
    if (-not $ijJar) { Fail "ImageJ 压缩包中没有找到 ij.jar。" }
    New-Item -ItemType Directory -Path $ImageJDir -Force | Out-Null
    Copy-Item -Path (Join-Path $ijJar.Directory.FullName "*") -Destination $ImageJDir -Recurse -Force
    if (-not (Test-Path -LiteralPath (Join-Path $ImageJDir "jre\bin\java.exe"))) {
        Write-Warn "ImageJ 已解压，但没有找到 java.exe；面积测量可能无法使用。"
    } else {
        Write-Ok "ImageJ 已安装到 $ImageJDir"
    }
}

# ---------------------------------------------------------------- models
Write-Step "5/6 下载模型"
$modelFailures = @()
if ($selectedModels.Count -eq 0) {
    Write-Warn "未选择模型；稍后可在界面中点击“检查 / 下载 当前模型”。"
} else {
    $modelDest = Join-Path $env:USERPROFILE ".cellpose\models"
    $downloader = Join-Path $App "download_model.py"
    foreach ($model in $selectedModels) {
        Write-Host ""
        Write-Host "--- $model" -ForegroundColor White
        & $venvPython $downloader --model $model --dest $modelDest --human
        if ($LASTEXITCODE -ne 0) {
            $modelFailures += $model
            Write-Warn "$model 下载失败；可以稍后在界面中重试。"
        } else {
            Write-Ok "$model 已就绪"
        }
    }
}

# ---------------------------------------------------------------- shortcut
Write-Step "6/6 创建快捷方式"
if (-not (Test-Path -LiteralPath $venvPythonw)) {
    $venvPythonw = $venvPython
}
$icon = Join-Path $App "assets\cellscope.ico"
$targetArgs = '"' + (Join-Path $App "app.py") + '"'
$mainLnk = Join-Path $InstallDir "CellScope.lnk"
New-Shortcut $mainLnk $venvPythonw $targetArgs $App $icon
Write-Ok "已创建：$mainLnk"

$programs = [Environment]::GetFolderPath("Programs")
if ($programs) {
    $menuDir = Join-Path $programs "CellScope"
    New-Item -ItemType Directory -Path $menuDir -Force | Out-Null
    New-Shortcut (Join-Path $menuDir "CellScope.lnk") $venvPythonw $targetArgs $App $icon
    Write-Ok "已创建开始菜单快捷方式"
}
if (-not $NoDesktopShortcut) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ($desktop) {
        New-Shortcut (Join-Path $desktop "CellScope.lnk") $venvPythonw $targetArgs $App $icon
        Write-Ok "已创建桌面快捷方式"
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host "  安装完成" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor DarkCyan
Write-Host "程序：$App"
Write-Host "Python：$Venv"
Write-Host "ImageJ：$(if ($NoImageJ) { '未安装（使用已有 ImageJ）' } else { $ImageJDir })"
Write-Host "启动：$mainLnk"
if ($modelFailures.Count -gt 0) {
    Write-Warn ("以下模型未完成，可在界面中重试：" + ($modelFailures -join ", "))
}
Write-Host "模型位置：$env:USERPROFILE\.cellpose\models"
Write-Host "推荐模型：cyto3"

if (-not $Unattended) {
    $launch = Read-Host "现在启动 CellScope？[Y/n]"
    if ($launch -notmatch '^[nN]') {
        Start-Process -FilePath $mainLnk
    }
    Read-Host "按回车关闭安装窗口"
}
