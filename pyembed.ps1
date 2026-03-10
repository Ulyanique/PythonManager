# Python Embeddable Manager - запуск из PowerShell
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
& python "$root\run.py" @args
exit $LASTEXITCODE
