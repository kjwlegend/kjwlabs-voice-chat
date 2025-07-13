#!/bin/bash

echo "🔥 火山引擎服务测试套件"
echo "============================================="

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "❌ 错误: Python未安装或不在PATH中"
        echo "请先安装Python 3.7+"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "✅ 使用Python: $PYTHON_CMD"

# 安装测试依赖
echo "📦 安装测试依赖..."
$PYTHON_CMD -m pip install -r tests/requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

# 运行测试脚本
echo "🚀 运行测试..."
$PYTHON_CMD run_tests.py

echo ""
echo "✅ 测试完成！" 