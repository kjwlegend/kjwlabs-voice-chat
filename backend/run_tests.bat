@echo off
echo 🔥 火山引擎服务测试套件
echo =============================================

REM 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: Python未安装或不在PATH中
    echo 请先安装Python 3.7+
    pause
    exit /b 1
)

REM 安装测试依赖
echo 📦 安装测试依赖...
pip install -r tests/requirements.txt

if %errorlevel% neq 0 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

REM 运行测试脚本
echo 🚀 运行测试...
python run_tests.py

echo.
echo ✅ 测试完成！
pause 