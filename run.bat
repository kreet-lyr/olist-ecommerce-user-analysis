@echo off
chcp 65001 > nul
setlocal

if not exist .venv\Scripts\python.exe (
    echo [1/2] 正在创建虚拟环境...
    py -m venv .venv
)

echo [2/2] 正在安装依赖并运行分析...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py

if errorlevel 1 (
    echo.
    echo 程序运行失败，请查看 outputs\pipeline.log。
) else (
    echo.
    echo 运行完成，请打开 outputs 文件夹查看图表、数据表和报告。
)
pause
