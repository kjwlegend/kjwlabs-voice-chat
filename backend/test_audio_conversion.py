#!/usr/bin/env python3
"""
测试音频格式转换功能
用于验证webm到wav的转换是否正常工作
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.volcengine_stt import STTAudioUtils, VolcengineSTTService

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_audio_conversion():
    """测试音频转换功能"""

    # 查找当前目录下的webm测试文件
    test_files = []
    for file_path in Path(".").glob("*.webm"):
        if file_path.is_file():
            test_files.append(file_path)

    if not test_files:
        logger.warning("未找到webm测试文件，尝试查找debug_audio文件...")
        for file_path in Path(".").glob("debug_audio*.webm"):
            if file_path.is_file():
                test_files.append(file_path)

    if not test_files:
        logger.error("未找到任何webm测试文件")
        return False

    logger.info(f"找到 {len(test_files)} 个webm测试文件")

    success_count = 0

    for test_file in test_files:
        logger.info(f"正在测试文件: {test_file}")

        try:
            # 读取webm文件
            with open(test_file, "rb") as f:
                webm_data = f.read()

            logger.info(f"读取webm文件成功，大小: {len(webm_data)} bytes")

            # 检测音频格式
            detected_format = STTAudioUtils.detect_audio_format(webm_data)
            logger.info(f"检测到的音频格式: {detected_format}")

            # 转换为WAV格式
            if detected_format != "wav":
                logger.info("开始转换音频格式...")
                wav_data = STTAudioUtils.convert_to_wav(webm_data, detected_format)
                logger.info(f"转换成功，WAV数据大小: {len(wav_data)} bytes")

                # 验证转换后的WAV格式
                if STTAudioUtils.judge_wav(wav_data):
                    logger.info("✅ WAV格式验证通过")

                    # 保存转换后的WAV文件
                    output_file = test_file.with_suffix(".converted.wav")
                    with open(output_file, "wb") as f:
                        f.write(wav_data)
                    logger.info(f"转换后的WAV文件已保存: {output_file}")

                    success_count += 1
                else:
                    logger.error("❌ WAV格式验证失败")
            else:
                logger.info("文件已是WAV格式，无需转换")
                success_count += 1

        except Exception as e:
            logger.error(f"❌ 处理文件 {test_file} 时出错: {str(e)}")

    logger.info(f"测试完成，成功: {success_count}/{len(test_files)}")
    return success_count == len(test_files)


async def test_stt_service():
    """测试STT服务的音频转换功能"""

    logger.info("测试STT服务的音频转换功能...")

    # 创建STT服务实例（测试模式）
    stt_service = VolcengineSTTService(
        access_key="test_key", app_id="test_app_id", test_mode=True
    )

    # 查找webm测试文件
    test_files = list(Path(".").glob("*.webm"))
    if not test_files:
        test_files = list(Path(".").glob("debug_audio*.webm"))

    if not test_files:
        logger.warning("未找到webm测试文件，跳过STT服务测试")
        return True

    test_file = test_files[0]
    logger.info(f"使用测试文件: {test_file}")

    try:
        # 读取webm文件
        with open(test_file, "rb") as f:
            webm_data = f.read()

        # 调用STT服务（测试模式）
        result = await stt_service.speech_to_text(webm_data)
        logger.info(f"STT服务返回结果: {result}")

        # 在测试模式下，应该返回模拟结果
        if "语音识别的模拟结果" in result:
            logger.info("✅ STT服务测试通过")
            return True
        else:
            logger.error("❌ STT服务测试失败")
            return False

    except Exception as e:
        logger.error(f"❌ STT服务测试异常: {str(e)}")
        return False


async def main():
    """主函数"""
    logger.info("开始测试音频转换功能...")

    # 检查FFmpeg是否可用
    try:
        import subprocess

        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ FFmpeg可用")
        else:
            logger.error("❌ FFmpeg不可用")
            return False
    except FileNotFoundError:
        logger.error("❌ FFmpeg未安装")
        logger.error("请确保系统已安装FFmpeg并添加到PATH")
        return False
    except Exception as e:
        logger.error(f"❌ FFmpeg检查失败: {str(e)}")
        return False

    # 测试音频转换功能
    conversion_success = await test_audio_conversion()

    # 测试STT服务
    stt_success = await test_stt_service()

    if conversion_success and stt_success:
        logger.info("🎉 所有测试通过！")
        return True
    else:
        logger.error("❌ 部分测试失败")
        return False


if __name__ == "__main__":
    asyncio.run(main())
