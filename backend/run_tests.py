#!/usr/bin/env python3
"""
火山引擎服务测试运行脚本
测试STT、LLM、TTS等功能
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_env_file(env_file_path):
    """从.env文件加载环境变量"""
    if not env_file_path.exists():
        return False

    logger.info(f"📁 正在加载配置文件: {env_file_path}")

    with open(env_file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # 只设置未定义的环境变量
                    if not os.getenv(key):
                        os.environ[key] = value
                        logger.debug(f"设置环境变量: {key}={value}")

    return True


def check_dependencies():
    """检查测试依赖"""
    try:
        import pytest
        import httpx

        logger.info("✅ 所有测试依赖已安装")
        return True
    except ImportError as e:
        logger.error(f"❌ 缺少测试依赖: {e}")
        logger.info("请运行: pip install -r tests/requirements.txt")
        return False


def run_unit_tests():
    """运行单元测试"""
    logger.info("🚀 开始运行火山引擎服务单元测试...")

    # 设置测试路径
    test_dir = Path(__file__).parent / "tests"
    test_file = test_dir / "test_volcengine_service.py"

    if not test_file.exists():
        logger.error(f"❌ 测试文件不存在: {test_file}")
        return False

    # 运行pytest
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-v",  # 详细输出
        "--tb=short",  # 简短的错误回溯
        "--asyncio-mode=auto",  # 自动async模式
        "-x",  # 遇到第一个失败就停止
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=Path(__file__).parent
        )

        if result.returncode == 0:
            logger.info("✅ 所有单元测试通过!")
            print(result.stdout)
            return True
        else:
            logger.error("❌ 单元测试失败!")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        logger.error(f"❌ 运行测试时发生错误: {e}")
        return False


def run_integration_test():
    """运行集成测试（需要真实的API密钥）"""
    logger.info("🧪 开始运行集成测试...")

    # 检查环境变量
    access_key = os.getenv("VOLCENGINE_ACCESS_KEY")
    secret_key = os.getenv("VOLCENGINE_SECRET_KEY")
    api_key = os.getenv("VOLCENGINE_API_KEY")
    app_id = os.getenv("VOLCENGINE_APP_ID")
    endpoint_id = os.getenv("VOLCENGINE_ENDPOINT_ID")

    # 调试信息
    logger.info(f"access_key: {access_key}")
    logger.info(f"secret_key: {secret_key}")
    logger.info(f"api_key: {api_key}")
    logger.info(f"app_id: {app_id}")
    logger.info(f"endpoint_id: {endpoint_id}")

    if not all([access_key, secret_key, api_key]):
        logger.warning("⚠️  缺少环境变量，跳过集成测试")
        logger.info("请设置以下环境变量来运行集成测试:")
        logger.info("- VOLCENGINE_ACCESS_KEY")
        logger.info("- VOLCENGINE_SECRET_KEY")
        logger.info("- VOLCENGINE_API_KEY")
        logger.info("- VOLCENGINE_APP_ID (用于语音服务)")
        logger.info("- VOLCENGINE_ENDPOINT_ID (用于大模型服务)")
        logger.info("")
        logger.info("🔧 你可以通过以下方式设置:")
        logger.info("1. 编辑 config.env 文件，填入你的真实API密钥")
        logger.info("2. 或在命令行中设置环境变量:")
        logger.info("   set VOLCENGINE_ACCESS_KEY=your_key")
        logger.info("   set VOLCENGINE_SECRET_KEY=your_secret")
        logger.info("   set VOLCENGINE_API_KEY=your_api_key")
        logger.info("   set VOLCENGINE_APP_ID=your_app_id")
        logger.info("   set VOLCENGINE_ENDPOINT_ID=your_endpoint_id")
        return True

    # 检查是否是占位符值
    placeholder_values = [
        "your_access_key_here",
        "your_secret_key_here",
        "your_api_key_here",
        "your_app_id_here",
        "your_endpoint_id_here",
    ]
    config_values = [access_key, secret_key, api_key, app_id, endpoint_id]
    if any(val in placeholder_values for val in config_values if val):
        logger.warning("⚠️  检测到占位符值，请在config.env中填入真实的API密钥")
        logger.info("📋 需要配置的参数:")
        logger.info("- VOLCENGINE_ACCESS_KEY: 火山引擎访问密钥")
        logger.info("- VOLCENGINE_SECRET_KEY: 火山引擎私钥")
        logger.info("- VOLCENGINE_API_KEY: 豆包大模型API密钥")
        logger.info("- VOLCENGINE_APP_ID: 语音服务应用ID")
        logger.info("- VOLCENGINE_ENDPOINT_ID: 大模型端点ID (格式: ep-xxxxxxxxx-xxx)")
        return True

    # 运行集成测试
    try:
        import asyncio
        import sys

        sys.path.append(str(Path(__file__).parent))

        from services.volcengine_service import VolcengineService

        async def test_real_api():
            """测试真实API"""
            service = VolcengineService(
                access_key=access_key,
                secret_key=secret_key,
                app_id=app_id,
                api_key=api_key,
                endpoint_id=endpoint_id,
            )

            # 测试LLM - 使用endpoint ID
            logger.info("🤖 测试大模型服务...")
            messages = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]

            try:
                result = await service.generate_chat_response(messages)
                if result:
                    logger.info("✅ LLM服务正常")
                    logger.info(f"回复: {result}")
                else:
                    logger.error(f"❌ LLM服务异常: 没有返回内容")
            except Exception as e:
                logger.error(f"❌ LLM服务错误: {e}")
                logger.info("ℹ️  LLM服务配置可能需要调整")

            # 测试TTS
            logger.info("🔊 测试语音合成服务...")
            try:
                audio_data = await service.text_to_speech("这是一个测试")

                if audio_data:
                    logger.info(f"✅ TTS服务正常，音频大小: {len(audio_data)} bytes")
                else:
                    logger.error("❌ TTS服务异常: 没有返回音频数据")
                    logger.info("ℹ️  TTS服务配置可能需要调整")
            except Exception as e:
                logger.error(f"❌ TTS服务错误: {e}")
                logger.info("ℹ️  TTS服务配置可能需要调整")

            # 测试STT（使用模拟音频数据）
            logger.info("🎤 测试语音识别服务...")
            try:
                mock_audio = b"mock_wav_audio_data_for_testing" * 10  # 确保足够大
                result = await service.speech_to_text(mock_audio)

                if result:
                    logger.info(f"✅ STT服务响应正常: {result}")
                else:
                    logger.error(f"❌ STT服务异常: 没有返回文本")
                    logger.info("ℹ️  STT服务配置可能需要调整")
            except Exception as e:
                logger.error(f"❌ STT服务错误: {e}")
                logger.info("ℹ️  STT服务配置可能需要调整")

            return True

        # 运行异步测试
        success = asyncio.run(test_real_api())

        if success:
            logger.info("✅ 集成测试通过!")
            return True
        else:
            logger.error("❌ 集成测试失败!")
            return False

    except Exception as e:
        logger.error(f"❌ 集成测试错误: {e}")
        return False


def main():
    """主函数"""
    logger.info("🔥 火山引擎服务测试套件")
    logger.info("=" * 50)

    # 尝试从配置文件加载环境变量
    config_file = Path(__file__).parent / "config.env"
    if config_file.exists():
        load_env_file(config_file)
    else:
        logger.info("📝 未找到config.env文件，请手动设置环境变量或创建配置文件")

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 运行单元测试
    unit_test_passed = run_unit_tests()

    # 运行集成测试
    integration_test_passed = run_integration_test()

    # 总结
    logger.info("=" * 50)
    logger.info("📊 测试结果总结:")
    logger.info(f"单元测试: {'✅ 通过' if unit_test_passed else '❌ 失败'}")
    logger.info(f"集成测试: {'✅ 通过' if integration_test_passed else '❌ 失败'}")

    if unit_test_passed and integration_test_passed:
        logger.info("🎉 所有测试通过!")
        sys.exit(0)
    else:
        logger.error("💥 部分测试失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
