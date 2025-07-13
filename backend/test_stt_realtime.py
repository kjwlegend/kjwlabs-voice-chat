#!/usr/bin/env python3
"""
实时STT服务测试脚本
用于验证修正后的STT服务是否能正常处理音频数据
"""

import asyncio
import sys
import os
import tempfile
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(".")

from services.volcengine_service import VolcengineService
from config import Config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_test_audio():
    """创建一个测试音频文件"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name

        # 使用FFmpeg生成一个简单的音频文件（1秒钟的440Hz正弦波）
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-y",
            output_path,
        ]

        logger.info(f"创建测试音频文件: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg创建音频失败: {result.stderr}")
            return None

        # 读取音频数据
        with open(output_path, "rb") as f:
            audio_data = f.read()

        # 清理临时文件
        os.unlink(output_path)

        logger.info(f"成功创建测试音频，大小: {len(audio_data)} bytes")
        return audio_data

    except Exception as e:
        logger.error(f"创建测试音频失败: {e}")
        return None


async def test_stt_with_real_audio():
    """使用真实音频测试STT服务"""
    logger.info("开始STT服务测试...")

    # 初始化配置
    config = Config()

    # 创建服务实例
    service = VolcengineService(
        access_key=config.VOLCENGINE_ACCESS_KEY,
        secret_key=config.VOLCENGINE_SECRET_KEY,
        app_id=config.VOLCENGINE_APP_ID,
        api_key=config.VOLCENGINE_API_KEY,
        endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
    )

    # 1. 测试服务连接
    logger.info("=" * 50)
    logger.info("1. 测试STT服务连接...")
    connection_result = await service.stt_service.test_connection()
    logger.info(f"连接测试结果: {connection_result}")

    # 2. 测试真实音频处理
    logger.info("=" * 50)
    logger.info("2. 测试真实音频处理...")

    # 创建测试音频
    audio_data = await create_test_audio()
    if not audio_data:
        logger.error("无法创建测试音频，跳过真实音频测试")
        return

    try:
        # 进行语音识别
        logger.info("开始语音识别...")
        result = await service.stt_service.speech_to_text(audio_data)
        logger.info(f"识别结果: {result}")

        # 3. 测试现有的WebM文件（如果存在）
        logger.info("=" * 50)
        logger.info("3. 测试现有的WebM文件...")

        webm_files = list(Path(".").glob("debug_audio_*.webm"))
        if webm_files:
            webm_file = webm_files[0]
            logger.info(f"发现WebM文件: {webm_file}")

            with open(webm_file, "rb") as f:
                webm_data = f.read()

            result = await service.stt_service.speech_to_text(webm_data)
            logger.info(f"WebM识别结果: {result}")
        else:
            logger.info("没有找到WebM文件")

    except Exception as e:
        logger.error(f"音频处理失败: {e}")

    logger.info("=" * 50)
    logger.info("STT服务测试完成")


if __name__ == "__main__":
    asyncio.run(test_stt_with_real_audio())
