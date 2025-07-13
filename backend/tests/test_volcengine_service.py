"""
火山引擎服务单元测试
测试STT、LLM、TTS和错误处理功能
"""

import pytest
import asyncio
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from services.volcengine_service import VolcengineService
import json

# 配置测试日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestVolcengineService:
    """火山引擎服务测试类"""

    def setup_method(self):
        """设置测试环境"""
        # 使用测试参数初始化服务，启用测试模式
        self.service = VolcengineService(
            access_key="test_access_key",
            secret_key="test_secret_key",
            app_id="test_app_id",
            api_key="test_api_key",
            endpoint_id="test_endpoint_id",
            test_mode=True,
        )

    @pytest.mark.asyncio
    async def test_init_service(self):
        """测试服务初始化"""
        assert self.service.access_key == "test_access_key"
        assert self.service.secret_key == "test_secret_key"
        assert self.service.app_id == "test_app_id"
        assert self.service.api_key == "test_api_key"
        assert self.service.endpoint_id == "test_endpoint_id"
        assert self.service.test_mode == True

        # 检查子服务初始化
        assert self.service.stt_service is not None
        assert self.service.tts_service is not None
        assert self.service.llm_service is not None

    @pytest.mark.asyncio
    async def test_llm_service_success(self):
        """测试LLM服务成功场景"""
        # 模拟成功响应
        mock_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "你好！我是豆包，很高兴为你服务。",
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # 创建模拟响应对象
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_instance.post.return_value = mock_response_obj

            # 测试LLM服务
            messages = [{"role": "user", "content": "你好"}]
            response = await self.service.generate_chat_response(messages)

            assert response == "你好！我是豆包，很高兴为你服务。"

            # 验证请求参数
            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert "chat/completions" in call_args[0][0]  # 第一个参数是URL
            assert call_args[1]["json"]["model"] == "test_endpoint_id"
            assert call_args[1]["json"]["messages"] == messages

    @pytest.mark.asyncio
    async def test_llm_service_no_api_key(self):
        """测试LLM服务没有api_key的场景"""
        service = VolcengineService(
            access_key="test_access_key",
            secret_key="test_secret_key",
            app_id="test_app_id",
            endpoint_id="test_endpoint_id",
            test_mode=True,
        )

        with pytest.raises(ValueError, match="LLM服务未初始化"):
            await service.generate_chat_response([{"role": "user", "content": "测试"}])

    @pytest.mark.asyncio
    async def test_llm_service_no_endpoint(self):
        """测试LLM服务没有endpoint_id的场景"""
        service = VolcengineService(
            access_key="test_access_key",
            secret_key="test_secret_key",
            app_id="test_app_id",
            api_key="test_api_key",
            test_mode=True,
        )

        with pytest.raises(ValueError, match="LLM服务未初始化"):
            await service.generate_chat_response([{"role": "user", "content": "测试"}])

    @pytest.mark.asyncio
    async def test_tts_service_success(self):
        """测试TTS服务成功场景"""
        # 模拟成功响应
        mock_response = {"data": "dGVzdF9hdWRpb19kYXRh"}  # base64编码的测试音频数据

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # 创建模拟响应对象
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_instance.post.return_value = mock_response_obj

            # 测试TTS服务
            audio_data = await self.service.text_to_speech("测试文本")

            # 验证返回的音频数据
            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0

            # 验证请求参数
            mock_instance.post.assert_called_once()
            call_args = mock_instance.post.call_args
            assert call_args[0][0] == "https://openspeech.bytedance.com/api/v1/tts"

            # 验证请求结构
            request_data = call_args[1]["json"]
            assert request_data["app"]["appid"] == "test_app_id"
            assert request_data["app"]["token"] == "access_token"
            assert request_data["request"]["text"] == "测试文本"
            assert (
                request_data["audio"]["voice_type"]
                == "zh_female_wanwanxiaohe_moon_bigtts"
            )

            # 验证认证头 - 应该使用access_key
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer;test_access_key"

    @pytest.mark.asyncio
    async def test_tts_service_error(self):
        """测试TTS服务错误场景"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # 创建模拟错误响应对象
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 400
            mock_response_obj.text = "参数错误"
            mock_instance.post.return_value = mock_response_obj

            with pytest.raises(Exception, match="TTS API请求失败"):
                await self.service.text_to_speech("测试文本")

    @pytest.mark.asyncio
    async def test_stt_service_mock(self):
        """测试STT服务模拟功能"""
        # 创建模拟音频数据
        audio_data = b"mock_audio_data_for_testing" * 10

        # 测试STT服务
        result = await self.service.speech_to_text(audio_data)

        # 验证返回的文本
        assert isinstance(result, str)
        assert "语音识别的模拟结果" in result
        assert str(len(audio_data)) in result

    @pytest.mark.asyncio
    async def test_stt_service_small_audio(self):
        """测试STT服务小音频数据场景"""
        # 创建小音频数据
        small_audio = b"small"

        # 测试STT服务
        result = await self.service.speech_to_text(small_audio)

        # 验证返回的文本
        assert result == "音频数据不足"

    @pytest.mark.asyncio
    async def test_service_integration(self):
        """测试服务集成"""
        # 模拟所有服务的成功响应
        mock_llm_response = {
            "choices": [{"message": {"role": "assistant", "content": "LLM正常工作"}}]
        }
        mock_tts_response = {"data": "dGVzdF9hdWRpb19kYXRh"}  # base64编码的测试音频数据

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # 设置多个调用的返回值
            mock_responses = [
                # LLM调用
                MagicMock(status_code=200, json=lambda: mock_llm_response),
                # TTS调用
                MagicMock(status_code=200, json=lambda: mock_tts_response),
            ]
            mock_instance.post.side_effect = mock_responses

            # 测试LLM
            llm_result = await self.service.generate_chat_response(
                [{"role": "user", "content": "测试"}]
            )
            assert llm_result == "LLM正常工作"

            # 测试TTS
            tts_result = await self.service.text_to_speech("测试")
            assert isinstance(tts_result, bytes)

            # 测试STT（模拟）
            stt_result = await self.service.speech_to_text(b"mock_audio" * 20)
            assert "语音识别的模拟结果" in stt_result

    @pytest.mark.asyncio
    async def test_service_test_method(self):
        """测试服务测试方法"""
        # 模拟各种响应
        mock_llm_response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "我是豆包，很高兴为你服务！",
                    }
                }
            ]
        }
        mock_tts_response = {"data": "dGVzdF9hdWRpb19kYXRh"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # 设置多个调用的返回值
            mock_responses = [
                # LLM调用
                MagicMock(status_code=200, json=lambda: mock_llm_response),
                # TTS调用
                MagicMock(status_code=200, json=lambda: mock_tts_response),
            ]
            mock_instance.post.side_effect = mock_responses

            # 测试服务状态
            results = await self.service.test_services()

            # 验证结果 - 新的格式
            assert results["llm"]["status"] == "✅ 连接正常"
            assert results["tts"]["status"] == "✅ 连接正常"
            assert results["stt"]["status"] == "✅ 连接正常"

            assert "我是豆包" in results["llm"]["response"]
            assert results["tts"]["audio_size"] > 0
            assert "语音识别的模拟结果" in results["stt"]["result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
