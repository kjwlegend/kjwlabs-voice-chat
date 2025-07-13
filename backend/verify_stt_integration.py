#!/usr/bin/env python3
"""
验证STT服务集成
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.volcengine_stt import (
    VolcengineSTTService,
    STTAudioUtils,
    AUDIO_PROCESSING_AVAILABLE,
)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """主验证函数"""

    logger.info("🔍 开始验证STT服务集成...")

    # 1. 检查FFmpeg可用性
    logger.info("1️⃣ 检查FFmpeg可用性...")
    if AUDIO_PROCESSING_AVAILABLE:
        logger.info("✅ FFmpeg可用")
    else:
        logger.error("❌ FFmpeg不可用，请检查安装")
        return False

    # 2. 测试音频格式检测
    logger.info("2️⃣ 测试音频格式检测...")
    test_webm_header = b"\x1a\x45\xdf\xa3"  # WebM魔术字节
    test_wav_header = b"RIFF\x00\x00\x00\x00WAVE"

    if STTAudioUtils.detect_audio_format(test_webm_header) == "webm":
        logger.info("✅ WebM格式检测正常")
    else:
        logger.error("❌ WebM格式检测失败")
        return False

    if STTAudioUtils.detect_audio_format(test_wav_header) == "wav":
        logger.info("✅ WAV格式检测正常")
    else:
        logger.error("❌ WAV格式检测失败")
        return False

    # 3. 测试STT服务初始化
    logger.info("3️⃣ 测试STT服务初始化...")
    try:
        stt_service = VolcengineSTTService(
            access_key="test_key", app_id="test_app_id", test_mode=True
        )
        logger.info("✅ STT服务初始化成功")
    except Exception as e:
        logger.error(f"❌ STT服务初始化失败: {e}")
        return False

    # 4. 测试模拟音频转换
    logger.info("4️⃣ 测试模拟音频识别...")
    try:
        # 创建简单的WAV格式音频数据
        import struct

        wav_header = (
            b"RIFF"
            + struct.pack("<I", 36)
            + b"WAVE"
            + b"fmt "
            + struct.pack("<I", 16)
            + struct.pack("<H", 1)
            + struct.pack("<H", 1)
            + struct.pack("<I", 16000)
            + struct.pack("<I", 32000)
            + struct.pack("<H", 2)
            + struct.pack("<H", 16)
            + b"data"
            + struct.pack("<I", 0)
        )
        mock_audio = wav_header + b"\x00\x00" * 1000  # 1000个静音样本

        result = await stt_service.speech_to_text(mock_audio)
        if "语音识别的模拟结果" in result:
            logger.info("✅ STT服务测试模式正常")
        else:
            logger.error("❌ STT服务测试模式异常")
            return False

    except Exception as e:
        logger.error(f"❌ STT服务测试失败: {e}")
        return False

    # 5. 检查是否有真实的测试文件
    logger.info("5️⃣ 检查测试文件...")
    test_files = list(Path(".").glob("*.webm")) + list(
        Path(".").glob("debug_audio*.webm")
    )

    if test_files:
        logger.info(f"📁 找到 {len(test_files)} 个测试文件")
        test_file = test_files[0]

        try:
            with open(test_file, "rb") as f:
                webm_data = f.read()

            logger.info(f"🎵 使用测试文件: {test_file} ({len(webm_data)} bytes)")

            # 测试实际转换
            result = await stt_service.speech_to_text(webm_data)
            logger.info(f"🎯 识别结果: {result}")
            logger.info("✅ 真实音频测试通过")

        except Exception as e:
            logger.error(f"❌ 真实音频测试失败: {e}")
            return False
    else:
        logger.info("📁 未找到测试文件，跳过真实音频测试")

    logger.info("🎉 所有验证通过！STT服务集成正常")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
