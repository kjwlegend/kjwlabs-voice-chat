"""
FastAPI主应用程序
实时对话AI助手后端服务
"""

import asyncio
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from typing import Dict, Any, Optional, List
from io import BytesIO
import subprocess
import tempfile
import os

# 导入服务模块
from services import VolcengineService
from config import config

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="EchoFlow AI Assistant", description="实时对话AI助手后端服务", version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
volcengine_service: Optional[VolcengineService] = None


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global volcengine_service

    logger.info("=== 🚀 EchoFlow AI Assistant Starting ===")
    config.print_config()

    # 初始化火山引擎服务
    if config.has_voice_config():
        try:
            volcengine_service = VolcengineService(
                access_key=config.VOLCENGINE_ACCESS_KEY,
                secret_key=config.VOLCENGINE_SECRET_KEY,
                app_id=config.VOLCENGINE_APP_ID,
                api_key=(
                    config.VOLCENGINE_API_KEY if config.VOLCENGINE_API_KEY else None
                ),
                endpoint_id=(
                    config.VOLCENGINE_ENDPOINT_ID
                    if config.VOLCENGINE_ENDPOINT_ID
                    else None
                ),
                n8n_webhook_url=config.N8N_WEBHOOK_URL,
            )

            logger.info("[Startup] 🔊 火山引擎语音服务初始化成功")

            if config.has_llm_config():
                logger.info("[Startup] 🤖 火山引擎LLM服务初始化成功")
            else:
                logger.warning("[Startup] ⚠️  LLM服务未配置，大模型对话功能将不可用")

            # 测试服务连接
            try:
                test_results = await volcengine_service.test_services()
                logger.info(f"[Startup] 🧪 服务测试结果: {test_results}")
            except Exception as test_error:
                logger.warning(f"[Startup] ⚠️  服务测试失败: {test_error}")

        except Exception as e:
            logger.error(f"[Startup] ❌ 火山引擎服务初始化失败: {e}")
            if not config.ENABLE_MOCK_SERVICES:
                raise HTTPException(status_code=500, detail="服务初始化失败")
    else:
        logger.warning("[Startup] ⚠️  火山引擎配置不完整，某些功能将不可用")
        logger.info(
            "[Startup] 请配置环境变量: VOLCENGINE_ACCESS_KEY, VOLCENGINE_SECRET_KEY, VOLCENGINE_APP_ID"
        )


# 存储WebSocket连接和对话状态
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.conversation_states: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        # 初始化对话状态
        self.conversation_states[client_id] = {
            "messages": [],  # 对话历史
            "current_audio_chunks": [],  # 当前音频块
            "is_processing": False,  # 是否正在处理
            "last_activity": asyncio.get_event_loop().time(),
        }

        logger.info(f"[ConnectionManager] 客户端 {client_id} 已连接")

        # 发送连接确认
        await self.send_message(
            client_id,
            {
                "type": "connection_established",
                "data": {"client_id": client_id, "status": "connected"},
            },
        )

    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.conversation_states:
            del self.conversation_states[client_id]
        logger.info(f"[ConnectionManager] 客户端 {client_id} 已断开连接")

    async def send_message(self, client_id: str, message: dict):
        """发送消息给客户端"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
                logger.debug(
                    f"[ConnectionManager] 发送消息给 {client_id}: {message['type']}"
                )
            except Exception as e:
                logger.error(f"[ConnectionManager] 发送消息失败 {client_id}: {e}")
                self.disconnect(client_id)

    def get_conversation_state(self, client_id: str) -> Dict[str, Any]:
        """获取对话状态"""
        return self.conversation_states.get(client_id, {})

    def update_conversation_state(self, client_id: str, updates: Dict[str, Any]):
        """更新对话状态"""
        if client_id in self.conversation_states:
            self.conversation_states[client_id].update(updates)


# 连接管理器实例
manager = ConnectionManager()


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "EchoFlow AI Assistant Backend is running",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    service_status = "available" if volcengine_service else "unavailable"
    llm_status = (
        "available" if volcengine_service and config.has_llm_config() else "unavailable"
    )
    voice_status = (
        "available"
        if volcengine_service and config.has_voice_config()
        else "unavailable"
    )

    return {
        "status": "healthy",
        "service": "EchoFlow AI Assistant",
        "volcengine_service": service_status,
        "llm_service": llm_status,
        "voice_service": voice_status,
        "timestamp": asyncio.get_event_loop().time(),
    }


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接处理"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.debug(
                f"[WebSocket] 收到客户端 {client_id} 消息: {message.get('type')}"
            )

            # 处理不同类型的消息
            await handle_message(client_id, message)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"[WebSocket] 客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"[WebSocket] 处理消息错误: {e}")
        manager.disconnect(client_id)


async def handle_message(client_id: str, message: dict):
    """处理WebSocket消息"""
    message_type = message.get("type")
    message_data = message.get("data", {})

    try:
        if message_type == "audio_chunk":
            # 处理音频流数据
            await process_audio_chunk(client_id, message_data)
        elif message_type == "interrupt":
            # 处理语音打断
            await process_interrupt(client_id)
        elif message_type == "start_conversation":
            # 开始对话
            await start_conversation(client_id)
        elif message_type == "end_conversation":
            # 结束对话
            await end_conversation(client_id)
        elif message_type == "heartbeat":
            # 心跳检测
            await manager.send_message(
                client_id,
                {
                    "type": "heartbeat_ack",
                    "data": {"timestamp": asyncio.get_event_loop().time()},
                },
            )
        else:
            logger.warning(f"[WebSocket] 未知消息类型: {message_type}")

    except Exception as e:
        logger.error(f"[WebSocket] 处理消息失败: {e}")
        await manager.send_message(
            client_id,
            {
                "type": "error",
                "data": {
                    "code": "PROCESSING_ERROR",
                    "message": f"处理消息失败: {str(e)}",
                    "retryable": True,
                },
            },
        )


async def process_audio_chunk(client_id: str, audio_data: dict):
    """处理音频流数据"""
    try:
        logger.debug(f"[AudioProcessor] 处理客户端 {client_id} 的音频数据")

        # 获取对话状态
        conv_state = manager.get_conversation_state(client_id)

        if conv_state.get("is_processing"):
            logger.debug(f"[AudioProcessor] 客户端 {client_id} 正在处理中，忽略音频块")
            return

        # 获取音频数据
        audio_base64 = audio_data.get("audioData")
        is_last = audio_data.get("isLast", False)

        if not audio_base64:
            logger.warning(f"[AudioProcessor] 客户端 {client_id} 发送的音频数据为空")
            # 如果是最后一块且为空，说明录制结束，开始处理累积的音频
            if is_last:
                await process_accumulated_audio(client_id)
            return

        # 解码音频数据
        try:
            audio_bytes = base64.b64decode(audio_base64)
            if len(audio_bytes) > 0:
                # 累积音频数据
                accumulated_audio = conv_state.get("accumulated_audio", b"")
                accumulated_audio += audio_bytes
                manager.update_conversation_state(
                    client_id, {"accumulated_audio": accumulated_audio}
                )
                logger.debug(
                    f"[AudioProcessor] 累积音频数据，总大小: {len(accumulated_audio)} bytes"
                )
        except Exception as decode_error:
            logger.error(f"[AudioProcessor] Base64解码失败: {str(decode_error)}")
            return

        if is_last:
            # 最后一个音频块，开始处理累积的音频
            await process_accumulated_audio(client_id)

    except Exception as e:
        logger.error(f"[AudioProcessor] 处理音频失败: {e}")
        manager.update_conversation_state(client_id, {"is_processing": False})
        await manager.send_message(
            client_id,
            {
                "type": "error",
                "data": {
                    "code": "AUDIO_PROCESSING_ERROR",
                    "message": f"音频处理失败: {str(e)}",
                    "retryable": True,
                },
            },
        )


async def process_accumulated_audio(client_id: str):
    """处理累积的音频数据"""
    try:
        logger.info(f"[AudioProcessor] 开始处理客户端 {client_id} 的完整音频")

        # 获取累积的音频数据
        conv_state = manager.get_conversation_state(client_id)
        accumulated_audio = conv_state.get("accumulated_audio", b"")

        if not accumulated_audio or len(accumulated_audio) == 0:
            logger.warning(f"[AudioProcessor] 客户端 {client_id} 没有累积的音频数据")
            return

        # 保存音频数据用于调试
        debug_audio_path = (
            f"debug_audio_{client_id}_{int(asyncio.get_event_loop().time())}.webm"
        )
        try:
            with open(debug_audio_path, "wb") as f:
                f.write(accumulated_audio)
            logger.info(f"[AudioProcessor] 音频数据已保存到: {debug_audio_path}")
        except Exception as save_error:
            logger.error(f"[AudioProcessor] 保存音频数据失败: {save_error}")

        # 标记为处理中
        manager.update_conversation_state(
            client_id,
            {"is_processing": True, "accumulated_audio": b""},  # 清空累积的音频
        )

        try:
            logger.info(
                f"[AudioProcessor] 处理音频数据，大小: {len(accumulated_audio)} bytes"
            )

            # 检查音频格式
            logger.info(f"[AudioProcessor] 音频数据前16字节: {accumulated_audio[:16]}")

            # 检查是否为WAV格式
            if accumulated_audio[:4] == b"RIFF" and accumulated_audio[8:12] == b"WAVE":
                logger.info("[AudioProcessor] 检测到WAV格式音频")
            else:
                logger.warning("[AudioProcessor] 音频格式不是WAV，可能影响STT识别效果")

            # 调用STT服务
            await manager.send_message(
                client_id,
                {"type": "stt_start", "data": {"message": "开始语音识别..."}},
            )

            if volcengine_service:
                # 直接调用新的语音识别方法，它会自动处理格式转换
                stt_text = await volcengine_service.speech_to_text(accumulated_audio)

                # 构建结果格式
                stt_result = {
                    "type": "final",
                    "text": stt_text,
                    "confidence": 0.95,
                    "is_final": True,
                }
            else:
                # 降级处理 - 模拟STT结果
                stt_result = {
                    "type": "final",
                    "text": "你好，这是语音识别的测试结果。当前音频大小: "
                    + str(len(accumulated_audio))
                    + " bytes",
                    "confidence": 0.8,
                    "is_final": True,
                }

            recognized_text = stt_result.get("text", "")
            logger.info(f"[AudioProcessor] STT结果: {recognized_text}")

            if not recognized_text or "模拟结果" in recognized_text:
                await manager.send_message(
                    client_id,
                    {"type": "stt_result", "data": stt_result},
                )
                # 如果是模拟结果，仍然继续处理，用于测试
                if "模拟结果" not in recognized_text:
                    return

            # 发送STT结果
            await manager.send_message(
                client_id, {"type": "stt_result", "data": stt_result}
            )

            # 调用LLM生成回复
            await process_llm_conversation(client_id, recognized_text)

        finally:
            # 处理完成，重置状态
            manager.update_conversation_state(client_id, {"is_processing": False})

    except Exception as e:
        logger.error(f"[AudioProcessor] 处理累积音频失败: {e}")
        manager.update_conversation_state(client_id, {"is_processing": False})
        await manager.send_message(
            client_id,
            {
                "type": "error",
                "data": {
                    "code": "AUDIO_PROCESSING_ERROR",
                    "message": f"音频处理失败: {str(e)}",
                    "retryable": True,
                },
            },
        )


async def convert_audio_to_wav(audio_data: bytes, input_path: str) -> Optional[bytes]:
    """
    将音频数据转换为WAV格式 - 统一使用STTAudioUtils

    Args:
        audio_data: 原始音频数据
        input_path: 输入文件路径（用于检测格式）

    Returns:
        Optional[bytes]: 转换后的WAV数据，失败时返回None
    """
    try:
        from services.volcengine_stt import STTAudioUtils

        logger.info("[AudioConverter] 开始音频格式转换")

        # 检测音频格式
        audio_format = STTAudioUtils.detect_audio_format(audio_data)
        logger.info(f"[AudioConverter] 检测到音频格式: {audio_format}")

        # 如果已经是WAV格式，直接返回
        if audio_format == "wav":
            logger.info("[AudioConverter] 音频已是WAV格式，无需转换")
            return audio_data

        # 使用STTAudioUtils转换
        wav_data = STTAudioUtils.convert_to_wav(audio_data, audio_format)

        logger.info(f"[AudioConverter] 转换成功，WAV数据大小: {len(wav_data)} bytes")

        # 保存转换后的WAV文件用于调试
        debug_wav_path = input_path.replace(".webm", "_converted.wav")
        with open(debug_wav_path, "wb") as f:
            f.write(wav_data)
        logger.info(f"[AudioConverter] 转换后的WAV文件已保存到: {debug_wav_path}")

        return wav_data

    except Exception as e:
        logger.error(f"[AudioConverter] 音频转换异常: {e}")
        return None


async def process_llm_conversation(client_id: str, user_text: str):
    """处理LLM对话（支持双路径响应）"""
    try:
        logger.info(f"[LLMProcessor] 处理客户端 {client_id} 的对话: {user_text}")

        # 获取对话历史
        conv_state = manager.get_conversation_state(client_id)
        messages = conv_state.get("messages", [])

        # 添加用户消息
        messages.append({"role": "user", "content": user_text})

        # 发送LLM处理开始信号
        await manager.send_message(
            client_id, {"type": "llm_start", "data": {"message": "AI正在思考..."}}
        )

        # 调用LLM服务
        if volcengine_service and config.has_llm_config():
            # 检查是否使用增强版LLM服务
            if volcengine_service.is_enhanced_llm_enabled():
                logger.info(f"[LLMProcessor] 使用双路径LLM响应")
                # 使用双路径响应
                await process_dual_path_llm_response(client_id, messages)
            else:
                logger.info(f"[LLMProcessor] 使用传统LLM响应")
                # 使用传统单一响应
                await process_traditional_llm_response(client_id, messages)
        else:
            # 降级处理
            ai_response = "你好！我是EchoFlow AI助手，很高兴为您服务。当前LLM服务未配置，这是一个模拟回复。"
            await process_fallback_llm_response(client_id, messages, ai_response)

    except Exception as e:
        logger.error(f"[LLMProcessor] 处理LLM对话失败: {e}")
        manager.update_conversation_state(client_id, {"is_processing": False})
        await manager.send_message(
            client_id,
            {
                "type": "error",
                "data": {
                    "code": "LLM_PROCESSING_ERROR",
                    "message": f"LLM处理失败: {str(e)}",
                    "retryable": True,
                },
            },
        )


async def process_dual_path_llm_response(
    client_id: str, messages: List[Dict[str, Any]]
):
    """处理双路径LLM响应"""
    try:
        logger.info(f"[LLMProcessor] 开始双路径LLM处理")

        # 定义即时响应回调（用于立即TTS）
        async def immediate_callback(immediate_text: str):
            logger.info(f"[LLMProcessor] 收到即时响应: {immediate_text[:100]}...")

            # 发送立即响应
            await manager.send_message(
                client_id,
                {
                    "type": "llm_immediate_response",
                    "data": {
                        "text": immediate_text,
                        "is_immediate": True,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                },
            )

            # 立即生成TTS音频
            await process_tts_generation(client_id, immediate_text, is_immediate=True)

        # 定义耐心等待回调
        async def patience_callback(patience_message: str):
            logger.info(f"[LLMProcessor] 耐心等待消息: {patience_message}")

            # 发送耐心等待消息
            await manager.send_message(
                client_id,
                {
                    "type": "llm_patience_update",
                    "data": {
                        "message": patience_message,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                },
            )

        # 调用双路径LLM服务
        dual_response = await volcengine_service.generate_dual_path_response(
            messages,
            immediate_callback=immediate_callback,
            patience_callback=patience_callback,
        )

        # 更新对话历史（使用最终响应）
        final_content = (
            dual_response.tool_response
            if dual_response.has_tool_calls
            else dual_response.immediate_response
        )
        messages.append({"role": "assistant", "content": final_content})
        manager.update_conversation_state(client_id, {"messages": messages})

        # 如果有工具调用，发送最终响应
        if dual_response.has_tool_calls:
            logger.info(
                f"[LLMProcessor] 发送最终融合响应: {dual_response.tool_response[:100]}..."
            )

            await manager.send_message(
                client_id,
                {
                    "type": "llm_final_response",
                    "data": {
                        "text": dual_response.tool_response,
                        "is_final": True,
                        "has_tool_calls": True,
                        "tool_execution_time": dual_response.tool_execution_time,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                },
            )

            # 生成最终响应的TTS音频
            await process_tts_generation(
                client_id, dual_response.tool_response, is_final=True
            )
        else:
            logger.info(f"[LLMProcessor] 无工具调用，双路径处理完成")

    except Exception as e:
        logger.error(f"[LLMProcessor] 双路径LLM处理失败: {e}")
        raise


async def process_traditional_llm_response(
    client_id: str, messages: List[Dict[str, Any]]
):
    """处理传统单一LLM响应"""
    try:
        ai_response = await volcengine_service.generate_chat_response(messages)

        if not ai_response:
            ai_response = "抱歉，我没能理解您的问题，请再说一遍。"

        logger.info(f"[LLMProcessor] 传统LLM回复: {ai_response[:100]}...")

        # 添加AI回复到对话历史
        messages.append({"role": "assistant", "content": ai_response})
        manager.update_conversation_state(client_id, {"messages": messages})

        # 发送LLM结果
        await manager.send_message(
            client_id,
            {
                "type": "llm_response",
                "data": {
                    "text": ai_response,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            },
        )

        # 调用TTS生成语音
        await process_tts_generation(client_id, ai_response)

    except Exception as e:
        logger.error(f"[LLMProcessor] 传统LLM处理失败: {e}")
        raise


async def process_fallback_llm_response(
    client_id: str, messages: List[Dict[str, Any]], ai_response: str
):
    """处理降级LLM响应"""
    try:
        logger.info(f"[LLMProcessor] 降级LLM回复: {ai_response[:100]}...")

        # 添加AI回复到对话历史
        messages.append({"role": "assistant", "content": ai_response})
        manager.update_conversation_state(client_id, {"messages": messages})

        # 发送LLM结果
        await manager.send_message(
            client_id,
            {
                "type": "llm_response",
                "data": {
                    "text": ai_response,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            },
        )

        # 调用TTS生成语音
        await process_tts_generation(client_id, ai_response)

    except Exception as e:
        logger.error(f"[LLMProcessor] LLM处理失败: {e}")
        await manager.send_message(
            client_id,
            {
                "type": "error",
                "data": {
                    "code": "LLM_PROCESSING_ERROR",
                    "message": f"AI回复生成失败: {str(e)}",
                    "retryable": True,
                },
            },
        )


async def process_tts_generation(
    client_id: str, text: str, is_immediate: bool = False, is_final: bool = False
):
    """处理TTS语音合成（支持双路径标记）"""
    try:
        # 确定TTS类型标记
        tts_type = "即时" if is_immediate else ("最终" if is_final else "常规")
        logger.info(
            f"[TTSProcessor] 为客户端 {client_id} 生成{tts_type}语音: {text[:50]}..."
        )

        # 发送TTS开始信号
        message_type = (
            "tts_immediate_start"
            if is_immediate
            else ("tts_final_start" if is_final else "tts_start")
        )

        await manager.send_message(
            client_id,
            {
                "type": message_type,
                "data": {
                    "message": f"正在生成{tts_type}语音...",
                    "is_immediate": is_immediate,
                    "is_final": is_final,
                },
            },
        )

        if volcengine_service:
            try:
                # 调用TTS服务
                audio_data = await volcengine_service.text_to_speech(text)

                if audio_data and len(audio_data) > 0:
                    # 编码音频数据
                    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

                    # 发送TTS结果
                    result_type = (
                        "tts_immediate_result"
                        if is_immediate
                        else ("tts_final_result" if is_final else "tts_result")
                    )

                    await manager.send_message(
                        client_id,
                        {
                            "type": result_type,
                            "data": {
                                "audioData": audio_base64,
                                "format": "mp3",
                                "isLast": True,
                                "is_immediate": is_immediate,
                                "is_final": is_final,
                                "text": text,  # 包含源文本用于前端显示
                            },
                        },
                    )
                    logger.info(
                        f"[TTSProcessor] {tts_type}TTS成功，音频大小: {len(audio_data)} bytes"
                    )
                else:
                    raise Exception("TTS服务返回空音频数据")

            except Exception as tts_error:
                logger.error(f"[TTSProcessor] TTS调用失败: {tts_error}")
                # 发送TTS不可用信号
                await manager.send_message(
                    client_id,
                    {
                        "type": "tts_unavailable",
                        "data": {"message": f"语音合成暂不可用: {str(tts_error)}"},
                    },
                )
        else:
            # 降级处理：只发送文本
            await manager.send_message(
                client_id,
                {
                    "type": "tts_unavailable",
                    "data": {"message": "语音合成服务暂不可用"},
                },
            )

    except Exception as e:
        logger.error(f"[TTSProcessor] TTS处理失败: {e}")
        await manager.send_message(
            client_id,
            {
                "type": "error",
                "data": {
                    "code": "TTS_PROCESSING_ERROR",
                    "message": f"语音合成失败: {str(e)}",
                    "retryable": True,
                },
            },
        )


async def process_interrupt(client_id: str):
    """处理语音打断"""
    logger.info(f"[InterruptProcessor] 处理客户端 {client_id} 的打断信号")

    # 停止当前处理
    manager.update_conversation_state(client_id, {"is_processing": False})

    # 发送打断确认
    await manager.send_message(
        client_id,
        {
            "type": "interrupt_acknowledged",
            "data": {"message": "打断已处理，可以继续说话"},
        },
    )


async def start_conversation(client_id: str):
    """开始对话"""
    logger.info(f"[ConversationManager] 客户端 {client_id} 开始对话")

    # 重置对话状态
    manager.update_conversation_state(
        client_id, {"messages": [], "is_processing": False}
    )

    await manager.send_message(
        client_id,
        {"type": "conversation_started", "data": {"message": "对话已开始，请开始说话"}},
    )


async def end_conversation(client_id: str):
    """结束对话"""
    logger.info(f"[ConversationManager] 客户端 {client_id} 结束对话")

    # 保存对话历史（可选）
    conv_state = manager.get_conversation_state(client_id)
    messages = conv_state.get("messages", [])
    if messages:
        logger.info(f"[ConversationManager] 对话包含 {len(messages)} 条消息")

    # 重置状态
    manager.update_conversation_state(
        client_id, {"messages": [], "is_processing": False}
    )

    await manager.send_message(
        client_id, {"type": "conversation_ended", "data": {"message": "对话已结束"}}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host=config.HOST, port=config.PORT, log_level=config.LOG_LEVEL.lower()
    )
