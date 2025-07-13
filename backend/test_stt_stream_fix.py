#!/usr/bin/env python3
"""
测试修正后的流式STT处理逻辑
验证是否解决了重复识别结果的问题
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

# 配置日志 - 设置为INFO级别以查看流式结果
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_speech_audio(text: str = "我是谁", duration: float = 2.0):
    """
    创建一个模拟语音的音频文件
    使用文本到语音或者简单的音频信号

    Args:
        text: 要模拟的文本内容
        duration: 音频时长（秒）

    Returns:
        bytes: 音频数据
    """
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name

        # 使用FFmpeg生成一个带有间隔的音频信号
        # 这样可以模拟真实的语音，让STT有内容可以识别
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration/4}",  # 第一个音调
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=523:duration={duration/4}",  # 第二个音调
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=659:duration={duration/4}",  # 第三个音调
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=784:duration={duration/4}",  # 第四个音调
            "-filter_complex",
            "[0:a][1:a][2:a][3:a]concat=n=4:v=0:a=1[out]",
            "-map",
            "[out]",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-y",
            output_path,
        ]

        logger.info(f"创建模拟语音音频文件...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"FFmpeg创建音频失败: {result.stderr}")
            return None

        # 读取音频数据
        with open(output_path, "rb") as f:
            audio_data = f.read()

        # 清理临时文件
        os.unlink(output_path)

        logger.info(f"成功创建模拟语音音频，大小: {len(audio_data)} bytes")
        return audio_data

    except Exception as e:
        logger.error(f"创建模拟语音音频失败: {e}")
        return None


async def test_stream_deduplication():
    """测试流式识别去重功能"""
    logger.info("=" * 60)
    logger.info("测试流式STT去重功能")
    logger.info("=" * 60)

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

    # 测试1: 使用现有的WebM文件（如果有的话）
    logger.info("\n📁 测试1: 处理现有的WebM文件...")
    webm_files = list(Path(".").glob("debug_audio_*.webm"))
    if webm_files:
        webm_file = webm_files[0]
        logger.info(f"发现WebM文件: {webm_file}")

        with open(webm_file, "rb") as f:
            webm_data = f.read()

        logger.info(f"WebM文件大小: {len(webm_data)} bytes")
        logger.info("开始处理WebM文件...")

        try:
            result = await service.stt_service.speech_to_text(webm_data)
            logger.info(f"🎯 最终识别结果: '{result}'")
        except Exception as e:
            logger.error(f"处理WebM文件失败: {e}")
    else:
        logger.info("没有找到WebM文件")

    # 测试2: 使用模拟的音频
    logger.info("\n🎵 测试2: 处理模拟音频...")
    audio_data = await create_speech_audio("我是谁", 3.0)
    if audio_data:
        try:
            logger.info("开始处理模拟音频...")
            result = await service.stt_service.speech_to_text(audio_data)
            logger.info(f"🎯 最终识别结果: '{result}'")
        except Exception as e:
            logger.error(f"处理模拟音频失败: {e}")
    else:
        logger.warning("无法创建模拟音频")

    # 测试3: 使用静音音频（确保基础功能正常）
    logger.info("\n🔇 测试3: 处理静音音频...")
    try:
        test_result = await service.stt_service.test_connection()
        logger.info(f"静音音频测试结果: {test_result['test_result']}")
    except Exception as e:
        logger.error(f"静音音频测试失败: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("✅ 流式STT去重测试完成")
    logger.info("=" * 60)

    print("\n📋 总结:")
    print("1. 查看上面的日志，确认每个流式结果都被正确记录")
    print("2. 确认最终结果没有重复内容")
    print("3. 如果还有重复，请检查火山引擎返回的具体数据格式")


if __name__ == "__main__":
    asyncio.run(test_stream_deduplication())
