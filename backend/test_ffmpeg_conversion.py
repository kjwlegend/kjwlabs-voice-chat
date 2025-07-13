#!/usr/bin/env python3
"""
快速测试FFmpeg音频转换功能
"""

import os
import sys
import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ffmpeg_conversion():
    """测试FFmpeg音频转换"""

    # 检查FFmpeg是否可用
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg未安装或不可用")
            return False
        logger.info("✅ FFmpeg可用")
    except FileNotFoundError:
        logger.error("❌ FFmpeg未安装")
        return False

    # 查找webm测试文件
    test_files = list(Path(".").glob("*.webm"))
    if not test_files:
        test_files = list(Path(".").glob("debug_audio*.webm"))

    if not test_files:
        logger.error("未找到webm测试文件")
        return False

    test_file = test_files[0]
    logger.info(f"使用测试文件: {test_file}")

    # 读取webm文件
    with open(test_file, "rb") as f:
        webm_data = f.read()

    logger.info(f"读取webm文件成功，大小: {len(webm_data)} bytes")

    # 转换为WAV
    try:
        wav_data = convert_webm_to_wav_ffmpeg(webm_data)
        logger.info(f"✅ 转换成功，WAV大小: {len(wav_data)} bytes")

        # 保存转换后的文件
        output_file = test_file.with_suffix(".converted.wav")
        with open(output_file, "wb") as f:
            f.write(wav_data)
        logger.info(f"转换后的WAV文件已保存: {output_file}")

        return True

    except Exception as e:
        logger.error(f"❌ 转换失败: {str(e)}")
        return False


def convert_webm_to_wav_ffmpeg(webm_data: bytes) -> bytes:
    """使用FFmpeg转换webm到wav"""

    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_input:
        temp_input.write(webm_data)
        temp_input.flush()
        input_path = temp_input.name

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_output:
        output_path = temp_output.name

    try:
        # FFmpeg命令
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            output_path,
        ]

        logger.info(f"执行命令: {' '.join(cmd)}")

        # 执行转换
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"FFmpeg转换失败: {result.stderr}")

        # 读取转换后的WAV数据
        with open(output_path, "rb") as f:
            wav_data = f.read()

        return wav_data

    finally:
        # 清理临时文件
        try:
            os.unlink(input_path)
            os.unlink(output_path)
        except:
            pass


if __name__ == "__main__":
    success = test_ffmpeg_conversion()
    if success:
        logger.info("🎉 测试通过！")
    else:
        logger.error("❌ 测试失败")
