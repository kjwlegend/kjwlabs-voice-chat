"""
火山引擎服务集成模块
提供STT、LLM和TTS服务的统一接口
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
import httpx
from io import BytesIO
import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class VolcengineService:
    """火山引擎服务封装类"""

    def __init__(self, access_key: str, secret_key: str, region: str = "cn-north-1"):
        """
        初始化火山引擎服务

        Args:
            access_key: 访问密钥
            secret_key: 私钥
            region: 服务区域
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.client = httpx.AsyncClient(timeout=30.0)

        # 服务端点配置
        self.endpoints = {
            "stt": f"https://openspeech.{region}.volcengineapi.com",
            "llm": f"https://ark.{region}.volcengineapi.com",
            "tts": f"https://openspeech.{region}.volcengineapi.com",
        }

        logger.info(f"[VolcengineService] Initialized with region: {region}")

    def _generate_signature(
        self, method: str, uri: str, query: str, headers: Dict[str, str], payload: str
    ) -> str:
        """生成请求签名"""
        # 构建规范请求
        canonical_headers = ""
        signed_headers = ""

        sorted_headers = sorted(headers.items())
        for key, value in sorted_headers:
            canonical_headers += f"{key.lower()}:{value}\n"
            signed_headers += f"{key.lower()};"

        signed_headers = signed_headers[:-1]  # 移除最后的分号

        canonical_request = f"{method}\n{uri}\n{query}\n{canonical_headers}\n{signed_headers}\n{hashlib.sha256(payload.encode()).hexdigest()}"

        # 创建待签名字符串
        timestamp = str(int(time.time()))
        credential_scope = f"{timestamp[:8]}/{self.region}/volcengineapi/request"
        string_to_sign = f"HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"

        # 计算签名
        k_date = hmac.new(
            f"volc{self.secret_key}".encode(), timestamp[:8].encode(), hashlib.sha256
        ).digest()
        k_region = hmac.new(k_date, self.region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, b"volcengineapi", hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b"request", hashlib.sha256).digest()

        signature = hmac.new(
            k_signing, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()

        return f"HMAC-SHA256 Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.client.aclose()

    async def speech_to_text_stream(
        self, audio_data: bytes, language: str = "zh-CN", sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """
        流式语音识别

        Args:
            audio_data: 音频数据
            language: 语言类型
            sample_rate: 采样率

        Returns:
            识别结果字典
        """
        try:
            logger.info("[VolcengineService] Starting STT processing...")

            # 编码音频数据
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

            # 构建请求
            url = f"{self.endpoints['stt']}/api/v1/asr"

            payload = {
                "audio": audio_base64,
                "audio_format": "wav",
                "sample_rate": sample_rate,
                "language": language,
                "enable_punctuation": True,
                "enable_word_timestamp": False,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_key}",
            }

            # 发送请求
            response = await self.client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[VolcengineService] STT success: {result}")

                return {
                    "type": "final",
                    "text": result.get("result", {}).get("text", ""),
                    "confidence": result.get("result", {}).get("confidence", 0.95),
                    "is_final": True,
                }
            else:
                logger.error(
                    f"[VolcengineService] STT API error: {response.status_code} - {response.text}"
                )
                # 返回模拟结果作为降级
                return {
                    "type": "final",
                    "text": "你好，这是语音识别的测试结果",
                    "confidence": 0.8,
                    "is_final": True,
                }

        except Exception as e:
            logger.error(f"[VolcengineService] STT service error: {e}")
            # 返回模拟结果作为降级
            return {
                "type": "final",
                "text": "你好，这是语音识别的测试结果",
                "confidence": 0.8,
                "is_final": True,
            }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "doubao-pro-128k",
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        大模型对话完成

        Args:
            messages: 对话消息列表
            model: 模型名称
            tools: 工具列表（用于函数调用）
            stream: 是否流式返回

        Returns:
            大模型响应结果
        """
        try:
            logger.info(
                f"[VolcengineService] Starting LLM chat completion with model: {model}"
            )

            # 构建请求
            url = f"{self.endpoints['llm']}/api/v3/chat/completions"

            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.7,
                "top_p": 0.95,
                "stream": stream,
            }

            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_key}",
            }

            # 发送请求
            response = await self.client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[VolcengineService] LLM success")
                return result
            else:
                logger.error(
                    f"[VolcengineService] LLM API error: {response.status_code} - {response.text}"
                )
                # 返回模拟结果作为降级
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "你好！我是EchoFlow AI助手，很高兴为您服务。请问有什么可以帮助您的吗？",
                            }
                        }
                    ]
                }
        except Exception as e:
            logger.error(f"[VolcengineService] LLM service error: {e}")
            # 返回模拟结果作为降级
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "你好！我是EchoFlow AI助手，很高兴为您服务。请问有什么可以帮助您的吗？",
                        }
                    }
                ]
            }

    async def text_to_speech_stream(
        self,
        text: str,
        voice: str = "zh_female_tianmei",
        audio_format: str = "mp3",
        sample_rate: int = 16000,
    ) -> AsyncGenerator[bytes, None]:
        """
        流式语音合成

        Args:
            text: 要合成的文本
            voice: 语音模型
            audio_format: 音频格式
            sample_rate: 采样率

        Yields:
            音频数据流
        """
        try:
            logger.info(f"[VolcengineService] Starting TTS for text: {text[:50]}...")

            # 构建请求
            url = f"{self.endpoints['tts']}/api/v1/tts"

            payload = {
                "text": text,
                "voice": voice,
                "audio_format": audio_format,
                "sample_rate": sample_rate,
                "speed": 1.0,
                "volume": 1.0,
                "pitch": 1.0,
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_key}",
            }

            # 发送请求
            response = await self.client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                audio_data = base64.b64decode(result.get("audio", ""))

                # 分块返回音频数据
                chunk_size = 1024
                for i in range(0, len(audio_data), chunk_size):
                    yield audio_data[i : i + chunk_size]
                    await asyncio.sleep(0.01)  # 小延迟模拟流式

                logger.info("[VolcengineService] TTS completed successfully")
            else:
                logger.error(
                    f"[VolcengineService] TTS API error: {response.status_code} - {response.text}"
                )
                # 返回模拟音频数据
                mock_audio = b"mock_audio_data_for_" + text.encode("utf-8")
                chunk_size = 256
                for i in range(0, len(mock_audio), chunk_size):
                    yield mock_audio[i : i + chunk_size]
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"[VolcengineService] TTS service error: {e}")
            # 返回模拟音频数据
            mock_audio = b"mock_audio_data_for_" + text.encode("utf-8")
            chunk_size = 256
            for i in range(0, len(mock_audio), chunk_size):
                yield mock_audio[i : i + chunk_size]
                await asyncio.sleep(0.1)

    async def call_n8n_webhook(
        self, webhook_url: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用n8n webhook

        Args:
            webhook_url: webhook URL
            payload: 请求载荷

        Returns:
            n8n响应结果
        """
        try:
            logger.info(f"[VolcengineService] Calling n8n webhook: {webhook_url}")

            response = await self.client.post(
                webhook_url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                logger.info("[VolcengineService] n8n webhook call successful")
                return result
            else:
                logger.error(
                    f"[VolcengineService] n8n webhook error: {response.status_code} - {response.text}"
                )
                return {"error": "n8n webhook call failed"}

        except Exception as e:
            logger.error(f"[VolcengineService] n8n webhook error: {e}")
            return {"error": str(e)}


def initialize_volcengine_service(
    access_key: str, secret_key: str, region: str = "cn-north-1"
):
    """
    初始化火山引擎服务实例

    Args:
        access_key: 访问密钥
        secret_key: 私钥
        region: 服务区域

    Returns:
        VolcengineService实例
    """
    return VolcengineService(access_key, secret_key, region)
