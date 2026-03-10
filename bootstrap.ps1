# Bootstrap: при первом запуске без Python скачивает embed 3.12.0 и запускает менеджер.
# Использование: .\bootstrap.ps1 [аргументы для run.py]
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PythonsRoot = if ($env:PYEMBED_ROOT) { $env:PYEMBED_ROOT } else { Join-Path $ScriptDir "pythons" }
$BootstrapVersion = "3.12.0"
$BootstrapDir = Join-Path $PythonsRoot $BootstrapVersion
$BootstrapExe = Join-Path $BootstrapDir "python.exe"
$RunPy = Join-Path $ScriptDir "run.py"

function Find-Python {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }
    if (Test-Path $BootstrapExe) { return $BootstrapExe }
    return $null
}

function Get-Arch {
    if ([Environment]::Is64BitOperatingSystem) { return "amd64" } else { return "win32" }
}

function Install-Bootstrap {
    $arch = Get-Arch
    $url = "https://www.python.org/ftp/python/$BootstrapVersion/python-$BootstrapVersion-embed-$arch.zip"
    $zipPath = Join-Path $PythonsRoot "python-$BootstrapVersion-embed.zip"

    Write-Host "Python не найден. Скачиваю $BootstrapVersion (embed, $arch) для первого запуска..."
    New-Item -ItemType Directory -Path $PythonsRoot -Force | Out-Null

    try {
        Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    } catch {
        Write-Host "Ошибка загрузки: $_" -ForegroundColor Red
        exit 1
    }

    Write-Host "Распаковка в $BootstrapDir ..."
    Expand-Archive -Path $zipPath -DestinationPath $BootstrapDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
    Write-Host "Готово. Запускаю менеджер."
}

$pythonExe = Find-Python
if (-not $pythonExe) {
    Install-Bootstrap
    $pythonExe = $BootstrapExe
}

& $pythonExe $RunPy @args
exit $LASTEXITCODE
