"""
火山引擎文本转语音(TTS)服务模块
提供语音合成功能
"""

import httpx
import json
import logging
import base64
import uuid
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class VolcengineTTSService:
    """火山引擎TTS服务"""

    def __init__(self, access_key: str, app_id: str):
        """
        初始化TTS服务

        Args:
            access_key: 访问密钥
            app_id: 应用ID
        """
        self.access_key = access_key
        self.app_id = app_id
        self.base_url = "https://openspeech.bytedance.com/api/v1/tts"

        # 默认TTS配置
        self.default_config = {
            "cluster": "volcano_tts",
            "voice_type": "zh_female_wanwanxiaohe_moon_bigtts",
            "encoding": "mp3",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
            "operation": "query",
            "with_frontend": 1,
            "frontend_type": "unitTson",
        }

        logger.info(f"[VolcengineTTS] 初始化完成 - App ID: {app_id}")
        logger.info(f"[VolcengineTTS] 🔊 Access Key: {access_key[:10]}...")

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        """
        文本转语音

        Args:
            text: 要转换的文本
            **kwargs: 其他参数 (voice_type, speed_ratio等)

        Returns:
            bytes: 音频数据
        """
        logger.info(f"[VolcengineTTS] 开始语音合成，文本: {text}")

        # 合并配置
        config = {**self.default_config, **kwargs}

        # 准备请求数据
        request_data = {
            "app": {
                "appid": self.app_id,
                "token": "access_token",  # 根据官方demo，这是字符串字面量
                "cluster": config["cluster"],
            },
            "user": {"uid": "demo_user_id"},
            "audio": {
                "voice_type": config["voice_type"],
                "encoding": config["encoding"],
                "speed_ratio": config["speed_ratio"],
                "volume_ratio": config["volume_ratio"],
                "pitch_ratio": config["pitch_ratio"],
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": config["operation"],
                "with_frontend": config["with_frontend"],
                "frontend_type": config["frontend_type"],
            },
        }

        # 请求头
        headers = {
            "Authorization": f"Bearer;{self.access_key}",  # 注意分号分隔
            "Content-Type": "application/json",
        }

        logger.info(f"[VolcengineTTS] 请求URL: {self.base_url}")
        logger.info(
            f"[VolcengineTTS] 请求参数: {json.dumps(request_data, ensure_ascii=False, indent=2)}"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url, json=request_data, headers=headers
                )
                logger.info(f"[VolcengineTTS] 响应状态: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    # logger.info(
                    #     f"[VolcengineTTS] 响应: {json.dumps(result, ensure_ascii=False, indent=2)}"
                    # )

                    if "data" in result:
                        # 解码base64音频数据
                        audio_data = base64.b64decode(result["data"])
                        logger.info(
                            f"[VolcengineTTS] 合成成功，音频大小: {len(audio_data)} bytes"
                        )
                        return audio_data
                    else:
                        logger.error(f"[VolcengineTTS] 响应中没有data字段: {result}")
                        raise Exception("TTS响应中没有音频数据")
                else:
                    error_text = response.text
                    logger.error(
                        f"[VolcengineTTS] API错误: {response.status_code} - {error_text}"
                    )
                    raise Exception(
                        f"TTS API请求失败: {response.status_code} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"[VolcengineTTS] 请求异常: {str(e)}")
            raise

    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表

        Returns:
            List[Dict[str, Any]]: 语音列表
        """
        # 这里返回一些常用的语音类型
        # 实际应用中可能需要调用专门的API获取
        return [
            {
                "voice_type": "zh_female_wanwanxiaohe_moon_bigtts",
                "name": "万万小荷",
                "gender": "female",
                "language": "zh",
                "description": "温柔甜美的女性声音",
            },
            {
                "voice_type": "zh_male_xiaofeng_moon_bigtts",
                "name": "小峰",
                "gender": "male",
                "language": "zh",
                "description": "清晰稳重的男性声音",
            },
            {
                "voice_type": "zh_female_xiaoyu_moon_bigtts",
                "name": "小雨",
                "gender": "female",
                "language": "zh",
                "description": "清新自然的女性声音",
            },
        ]

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试连接状态

        Returns:
            Dict[str, Any]: 测试结果
        """
        logger.info("[VolcengineTTS] 测试连接...")

        try:
            test_text = "这是一个测试"
            audio_data = await self.text_to_speech(test_text)

            return {
                "status": "✅ 连接正常",
                "audio_size": len(audio_data),
                "test_text": test_text,
                "error": None,
            }

        except Exception as e:
            logger.error(f"[VolcengineTTS] 连接测试失败: {str(e)}")
            return {
                "status": "❌ 连接异常",
                "audio_size": 0,
                "test_text": None,
                "error": str(e),
            }
