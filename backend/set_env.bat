@echo off
echo 🔧 设置火山引擎环境变量
echo ================================

REM 请在下面替换为你的真实API密钥
set VOLCENGINE_ACCESS_KEY=your_access_key_here
set VOLCENGINE_SECRET_KEY=your_secret_key_here
set VOLCENGINE_API_KEY=your_api_key_here
set VOLCENGINE_REGION=cn-beijing

echo ✅ 环境变量已设置:
echo VOLCENGINE_ACCESS_KEY=%VOLCENGINE_ACCESS_KEY%
echo VOLCENGINE_SECRET_KEY=%VOLCENGINE_SECRET_KEY%
echo VOLCENGINE_API_KEY=%VOLCENGINE_API_KEY%
echo VOLCENGINE_REGION=%VOLCENGINE_REGION%

echo.
echo ⚠️  注意: 这些变量只在当前会话中有效
echo 关闭命令窗口后需要重新设置

echo.
echo 🚀 现在可以运行测试了: python run_tests.py
echo. 