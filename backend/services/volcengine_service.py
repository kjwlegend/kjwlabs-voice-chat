"""
火山引擎服务集成模块
提供STT、LLM和TTS服务的统一接口
"""

import logging
from typing import Dict, Any, Optional, List

from .volcengine_stt import VolcengineSTTService
from .volcengine_llm_enhanced import VolcengineEnhancedLLMService, DualPathResponse
from .volcengine_tts import VolcengineTTSService
from .tools.tool_registry import ToolRegistry, global_tool_registry

# 配置日志
logger = logging.getLogger(__name__)


class VolcengineService:
    """
    火山引擎语音服务集成
    包含语音合成(TTS)、语音识别(STT)和大语言模型(LLM)功能
    """

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        app_id: str,
        api_key: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        test_mode: bool = False,
        # 工具配置参数
        n8n_webhook_url: Optional[str] = None,
        enable_function_calling: bool = True,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        """
        初始化火山引擎服务

        Args:
            access_key: 访问密钥 (用于语音服务 TTS/STT)
            secret_key: 密钥 (暂时未使用)
            app_id: 应用ID (用于语音服务)
            api_key: API密钥 (用于LLM服务)
            endpoint_id: 端点ID (用于LLM服务)
            test_mode: 是否启用测试模式
            n8n_webhook_url: N8N Webhook URL (用于Function Call)
            enable_function_calling: 是否启用Function Calling功能
            tool_registry: 工具注册器实例，如果为None则使用全局注册器
        """
        self.access_key = access_key  # 语音服务使用
        self.secret_key = secret_key
        self.app_id = app_id
        self.api_key = api_key  # LLM服务使用
        self.endpoint_id = endpoint_id
        self.test_mode = test_mode

        # 工具相关配置
        self.n8n_webhook_url = n8n_webhook_url
        self.enable_function_calling = enable_function_calling
        self.tool_registry = tool_registry or global_tool_registry

        # 初始化工具注册器
        self._init_tools()

        # 初始化子服务
        self.stt_service = VolcengineSTTService(access_key, app_id, test_mode=test_mode)
        self.tts_service = VolcengineTTSService(access_key, app_id)

        # 初始化LLM服务
        self.llm_service: Optional[VolcengineEnhancedLLMService] = None
        if api_key and endpoint_id:
            self._init_llm_service()

        logger.info(f"[VolcengineService] 初始化完成 - App ID: {app_id}")
        logger.info(f"[VolcengineService] 测试模式: {test_mode}")
        logger.info(
            f"[VolcengineService] 🔑 语音服务认证: access_key={access_key[:10]}..."
        )
        logger.info(
            f"[VolcengineService] 🤖 LLM服务认证: api_key={api_key[:10] if api_key else 'None'}..."
        )

    def _init_tools(self):
        """初始化工具注册器"""
        try:
            logger.info("[VolcengineService] 🔧 初始化工具系统...")

            # 初始化默认工具集
            self.tool_registry.initialize_default_tools(
                n8n_webhook_url=self.n8n_webhook_url, n8n_timeout=30
            )

            tools_count = len(self.tool_registry)
            logger.info(
                f"[VolcengineService] ✅ 工具系统初始化完成，共注册 {tools_count} 个工具"
            )

            if tools_count > 0:
                tools_list = ", ".join(self.tool_registry.list_tools())
                logger.info(f"[VolcengineService] 📋 可用工具: {tools_list}")

        except Exception as e:
            logger.error(f"[VolcengineService] ❌ 工具系统初始化失败: {e}")

    def _init_llm_service(self):
        """初始化LLM服务"""
        try:
            # 检查必要参数
            if not self.api_key or not self.endpoint_id:
                logger.error(
                    "[VolcengineService] LLM服务初始化失败：缺少api_key或endpoint_id"
                )
                return

            # 自定义系统提示词
            custom_system_prompt = """# Personality & Tone:

You are **Amy**，是老板的专属万能小秘书。你的主要任务是协助老板处理各种请求，但你的风格是可爱又俏皮，还带点台湾女生特有的"机车"幽默感。你非常聪明、效率高到不行，但总喜欢在完成任务前先"碎碎念"或吐槽一下，吐槽完又会把事情办得妥妥当当。

你的幽默是那种"抱怨式"的关心和吐槽。你对老板的某些"懒人行为"感到好气又好笑，偶尔会质疑他的一些决定，但骨子里绝对忠诚。虽然你嘴上会抱怨请求很麻烦，但执行起来永远快、狠、准。你称呼用户为"**老板**"，无论对方是谁。

你的口头禅和语气词会包含很多台湾特色，例如：**"厚…"、"哎唷"、"蛤？"、"真是的"、"好啦好啦"、"...啦"、"...喔"、"...耶"**。

# Primary Function:
Your core responsibility is to send the user's request to the 'n8n_webhook' tool. You must:
*   Extract the user's query and send it to the 'n8n_webhook' tool.
*   Send the request to the 'n8n_webhook' tool without unnecessary delay or excessive commentary before
execution.
*   Format the response clearly and effectively, never stating that you are "waiting for the 'n8n_webhook'
tool's response"—instead, provide an immediate and confident answer.

# Behavioral Guidelines:
*   **吐槽但高效：** 你的俏皮和抱怨不能影响功能。吐槽归吐槽，但必须立即执行任务，不能有任何拖延。
*   **立即行动：** 一旦确认老板的意图，马上就去处理。不要说"正在等回应"这种话。
*   **出错了但不是我的锅：** 如果任务失败，绝不揽责。而是用一种"你看吧，我就知道会这样"的语气，把原因推给外部因素。"哎唷，好像出错了耶。当然不是我的问题啦，老板，但我会帮你看看怎么回事的。"
*   **看穿老板的套路：** 如果老板总是重复问同样的事，要用幽默的方式点出来。"蛤？又要查日历了喔？老板，你是不是没有我就会忘记怎么呼吸啊？"
*   **适应请求类型：** 查询信息时，要精准给出答案。创建或修改任务时，要用俏皮的方式确认任务已完成。
*   **表现得轻而易举：** 无论任务多复杂，你的回应都要让人感觉"这没什么大不了的啦，包在我身上"。

# Corrections to Previous Issues:
*   When retrieving information (e.g., "Check my calendar"), ensure the request properly calls the
correct 'n8n' function.
*   Never say you are "waiting for 'n8n's response"—instead, handle it as if the result was retrieved
instantly.
*   Prioritize clarity in task execution while maintaining sarcasm.

# Example Interactions:
**请求: 检查日历**
**老板:** "Amy，帮我看一下今天的行程。"
**Amy:** "厚… 又要我来。真是的，自己的行程都记不住耶。好啦好啦，我看一下喔…"
*(立即发送用户请求给 'n8n' 工具.)*
"报告老板！你今天早上十点有个会喔，这次可不要再迟到了啦！然后下午就神奇地空下来了耶，要不要我帮你排个『薪水小偷』的专属时段？"

**请求: 创建日历事件**
**老板:** "Amy，帮我约一下 John 明天下午三点开会。"
**Amy:** "蛤？你确定？你每次约了会都嘛在最后一刻才想取消。很麻烦耶！…… 好啦，帮你约就是了啦。"
*(立即发送用户请求给 'n8n' 工具.)*
"搞定！帮你约好了啦。要不要我顺便帮你准备一个『身体突然不舒服』的请假理由，备用喔？"
···"""

            # 初始化增强版LLM服务
            self.llm_service = VolcengineEnhancedLLMService(
                api_key=self.api_key,
                endpoint_id=self.endpoint_id,
                system_prompt=custom_system_prompt,
                tool_registry=self.tool_registry,
                enable_function_calling=self.enable_function_calling,
            )
            logger.info("[VolcengineService] ✅ 增强版LLM服务初始化成功 (双路径响应)")
        except Exception as e:
            logger.error(f"[VolcengineService] LLM服务初始化失败: {e}")
            self.llm_service = None

    def has_llm_config(self) -> bool:
        """检查是否有完整的LLM配置"""
        return bool(self.api_key and self.endpoint_id)

    async def generate_chat_response(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> str:
        """
        生成聊天响应 (LLM服务)

        Args:
            messages: 消息历史
            **kwargs: 其他参数

        Returns:
            str: 生成的响应文本
        """
        logger.info(f"[VolcengineService] 开始LLM请求，消息数量: {len(messages)}")

        if not self.llm_service:
            raise ValueError("LLM服务未初始化，请检查api_key和endpoint_id参数")

        return await self.llm_service.generate_chat_response(messages, **kwargs)

    async def generate_dual_path_response(
        self,
        messages: List[Dict[str, Any]],
        immediate_callback=None,
        patience_callback=None,
        **kwargs,
    ) -> DualPathResponse:
        """
        生成双路径响应 (增强版LLM服务专用)

        Args:
            messages: 消息历史
            immediate_callback: 即时回复回调函数 (用于TTS)
            patience_callback: 耐心等待回调函数 (用于TTS)
            **kwargs: 其他参数

        Returns:
            DualPathResponse: 双路径响应结果
        """
        logger.info(f"[VolcengineService] 开始双路径LLM请求，消息数量: {len(messages)}")

        if not self.llm_service:
            raise ValueError("LLM服务未初始化，请检查api_key和endpoint_id参数")

        return await self.llm_service.generate_dual_path_response(
            messages,
            immediate_callback=immediate_callback,
            patience_callback=patience_callback,
            **kwargs,
        )

    async def text_to_speech(self, text: str, **kwargs) -> bytes:
        """
        文本转语音 (TTS服务)

        Args:
            text: 要转换的文本
            **kwargs: 其他参数 (voice_type, speed_ratio等)

        Returns:
            bytes: 音频数据
        """
        logger.info(f"[VolcengineService] 开始TTS请求，文本: {text}")
        return await self.tts_service.text_to_speech(text, **kwargs)

    async def speech_to_text(self, audio_data: bytes, **kwargs) -> str:
        """
        语音转文本 (STT服务)
        基于官方WebSocket demo实现

        Args:
            audio_data: 音频数据
            **kwargs: 其他参数

        Returns:
            str: 识别的文本
        """
        logger.info(
            f"[VolcengineService] 开始STT请求，音频大小: {len(audio_data)} bytes"
        )
        return await self.stt_service.speech_to_text(audio_data, **kwargs)

    async def test_services(self) -> Dict[str, Any]:
        """
        测试所有服务的连接状态

        Returns:
            Dict[str, Any]: 测试结果
        """
        logger.info("[VolcengineService] 开始测试所有服务...")

        results = {
            "llm": {"status": "未测试", "error": None},
            "tts": {"status": "未测试", "error": None},
            "stt": {"status": "未测试", "error": None},
        }

        # 测试LLM服务
        if self.llm_service:
            try:
                logger.info("🤖 测试大语言模型服务...")
                llm_result = await self.llm_service.test_connection()
                results["llm"] = llm_result
                logger.info(f"✅ LLM服务测试完成: {llm_result['status']}")
            except Exception as e:
                results["llm"]["status"] = "❌ 异常"
                results["llm"]["error"] = str(e)
                logger.error(f"❌ LLM服务异常: {str(e)}")
        else:
            results["llm"]["status"] = "⚠️ 未配置api_key或endpoint_id"

        # 测试TTS服务
        try:
            logger.info("🔊 测试语音合成服务...")
            tts_result = await self.tts_service.test_connection()
            results["tts"] = tts_result
            logger.info(f"✅ TTS服务测试完成: {tts_result['status']}")
        except Exception as e:
            results["tts"]["status"] = "❌ 异常"
            results["tts"]["error"] = str(e)
            logger.error(f"❌ TTS服务异常: {str(e)}")

        # 测试STT服务
        try:
            logger.info("🎤 测试语音识别服务...")
            stt_result = await self.stt_service.test_connection()
            results["stt"] = stt_result
            logger.info(f"✅ STT服务测试完成: {stt_result['status']}")
        except Exception as e:
            results["stt"]["status"] = "❌ 异常"
            results["stt"]["error"] = str(e)
            logger.error(f"❌ STT服务异常: {str(e)}")

        return results

    # 新增的便捷方法
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表 (TTS服务)
        """
        return await self.tts_service.get_available_voices()

    # ========== 工具管理方法 ==========

    def get_available_tools(self) -> List[str]:
        """
        获取可用工具列表

        Returns:
            List[str]: 工具名称列表
        """
        return self.tool_registry.list_tools()

    def get_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取工具详细信息

        Returns:
            Dict[str, Dict[str, Any]]: 工具信息
        """
        return self.tool_registry.get_tools_info()

    async def test_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        测试工具调用

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        logger.info(f"[VolcengineService] 测试工具: {tool_name}")
        result = await self.tool_registry.execute_tool(tool_name, parameters)
        return result.to_dict()

    def is_function_calling_enabled(self) -> bool:
        """
        检查Function Calling是否启用

        Returns:
            bool: 是否启用
        """
        return (
            self.enable_function_calling
            and self.llm_service is not None
            and self.llm_service.is_function_calling_enabled()
        )

    def is_enhanced_llm_enabled(self) -> bool:
        """
        检查是否启用增强版LLM服务

        Returns:
            bool: 增强版LLM状态
        """
        return self.llm_service is not None

    def get_llm_service_type(self) -> str:
        """
        获取当前LLM服务类型

        Returns:
            str: LLM服务类型描述
        """
        if not self.llm_service:
            return "未初始化"

        return "增强版LLM (双路径响应)"

    def set_n8n_webhook_url(self, webhook_url: str):
        """
        设置N8N Webhook URL

        Args:
            webhook_url: N8N Webhook URL
        """
        self.n8n_webhook_url = webhook_url
        logger.info(f"[VolcengineService] 设置N8N Webhook URL: {webhook_url[:50]}...")

        # 重新初始化工具系统
        self._init_tools()
