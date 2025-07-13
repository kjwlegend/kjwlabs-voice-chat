"""
火山引擎大语言模型(LLM)增强服务模块
基于OpenAI SDK，实现双路径响应机制，优化语音对话体验

核心功能：
1. 使用OpenAI SDK替代直接HTTP请求
2. 双路径响应：即时回复 + 异步工具调用
3. 智能融合：工具结果与对话的自然整合
4. 耐心管理：长时间等待的用户体验优化
"""

import os
import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI
from .tools.tool_registry import ToolRegistry, global_tool_registry
from .tools.tool_base import ToolResult
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

logger = logging.getLogger(__name__)


class ResponseType(Enum):
    """响应类型枚举"""

    SIMPLE = "simple"  # 简单对话，无需工具
    DUAL_PATH = "dual_path"  # 双路径：即时响应 + 工具调用


@dataclass
class DualPathResponse:
    """双路径响应结果"""

    immediate_response: str  # 即时回复内容
    tool_response: Optional[str] = None  # 工具调用后的完整回复
    has_tool_calls: bool = False  # 是否包含工具调用
    tool_execution_time: float = 0.0  # 工具执行时间


class PatienceManager:
    """耐心等待管理器 - 管理长时间工具调用期间的用户体验"""

    def __init__(self):
        """初始化耐心管理器"""
        # Amy的各种等待回复，体现她的俏皮性格
        self.patience_messages = [
            "这个查起来有点复杂，再等我一下下...",
            "哎呀，怎么这么慢啊，我催催看...",
            "真是的，这个系统也太慢了吧，快好了快好了",
            "老板你再等等，我正在努力查呢！",
            "厚...这比我想象的还要久耶",
        ]

        # 时间阈值设置（秒）
        self.thresholds = [5, 10, 15, 20, 25]

        logger.info("[PatienceManager] 耐心管理器初始化完成")

    async def handle_long_wait(
        self, elapsed_time: float, callback: Callable[[str], Awaitable[None]]
    ):
        """
        处理长时间等待

        Args:
            elapsed_time: 已等待时间（秒）
            callback: 发送耐心消息的回调函数
        """
        for i, threshold in enumerate(self.thresholds):
            if elapsed_time >= threshold and i < len(self.patience_messages):
                message = self.patience_messages[i]
                logger.info(
                    f"[PatienceManager] 触发耐心消息 ({elapsed_time:.1f}s): {message}"
                )
                await callback(message)
                break


class ImmediateResponseManager:
    """即时响应管理器 - 处理链路A（即时回复）"""

    def __init__(
        self, openai_client: AsyncOpenAI, endpoint_id: str, system_prompt: str
    ):
        """
        初始化即时响应管理器

        Args:
            openai_client: OpenAI客户端
            endpoint_id: 模型端点ID
            system_prompt: 系统提示词
        """
        self.client = openai_client
        self.endpoint_id = endpoint_id
        self.system_prompt = system_prompt

        logger.info("[ImmediateResponseManager] 即时响应管理器初始化完成")

    async def generate_immediate_response(
        self, user_input: str, context: List[Dict[str, Any]]
    ) -> str:
        """
        生成即时响应（链路A） - 基于system_prompt快速生成俏皮的"查询中"回复

        Args:
            user_input: 用户输入
            context: 对话上下文

        Returns:
            str: 即时响应内容
        """
        logger.info("[ImmediateResponseManager] 生成即时响应")

        # 构建快速响应prompt
        quick_prompt = f"""
{self.system_prompt}

用户刚刚发送了请求："{user_input}"

你检测到需要使用工具来查询信息。请快速生成一个俏皮的"查询中"回复，体现Amy的特色。

要求：
2. 符合Amy的俏皮人设和台湾腔调
3. 表示正在查询/处理中
4. 不要使用任何工具，只是一个过渡回复
5. 要让用户感觉你马上就要去查了

直接给出回复，不要解释。
"""

        logger.info(f"[ImmediateResponseManager] 快速响应prompt: {quick_prompt}")

        try:
            response = await self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=[{"role": "user", "content": quick_prompt}],  # type: ignore
                temperature=0.3,  # 较低temperature保证稳定性
                max_tokens=50,  # 限制token确保速度
                top_p=0.8,
            )

            immediate_reply = (
                response.choices[0].message.content or "好啦好啦，稍等一下下"
            )

            logger.info(f"[ImmediateResponseManager] 即时回复: {immediate_reply}")
            return immediate_reply

        except Exception as e:
            logger.error(f"[ImmediateResponseManager] 生成即时响应失败: {str(e)}")
            # 如果快速生成失败，使用简单备用回复
            fallback_replies = [
                "厚...让我查一下喔",
                "好啦好啦，稍等一下下",
                "等我一下，马上就好",
            ]
            import random

            return random.choice(fallback_replies)


class AsyncToolManager:
    """异步工具管理器 - 处理链路B（工具调用）"""

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        endpoint_id: str,
        system_prompt: str,
        tool_registry: ToolRegistry,
    ):
        """
        初始化异步工具管理器

        Args:
            openai_client: OpenAI客户端
            endpoint_id: 模型端点ID
            system_prompt: 系统提示词
            tool_registry: 工具注册器
        """
        self.client = openai_client
        self.endpoint_id = endpoint_id
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry
        self.patience_manager = PatienceManager()

        logger.info("[AsyncToolManager] 异步工具管理器初始化完成")

    async def execute_tool_calls_async(
        self,
        messages: List[Dict[str, Any]],
        patience_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Tuple[bool, str, List[ToolResult]]:
        """
        异步执行工具调用（链路B）

        Args:
            messages: 消息历史
            patience_callback: 耐心等待回调函数

        Returns:
            Tuple[bool, str, List[Dict]]: (是否有工具调用, 响应内容, 工具调用结果)
        """
        logger.info("[AsyncToolManager] 开始异步工具调用流程")
        start_time = time.time()

        try:
            # 准备消息（包含系统提示词）
            prepared_messages = self._prepare_messages_with_system_prompt(messages)

            # 获取工具定义
            tools_schemas = self.tool_registry.get_tools_schemas()

            # 调用LLM进行Function Call判断
            response = await self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=prepared_messages,  # type: ignore
                tools=[
                    {"type": "function", "function": schema} for schema in tools_schemas
                ],  # type: ignore
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000,
            )

            message = response.choices[0].message

            # 检查是否有工具调用
            if not message.tool_calls:
                logger.info("[AsyncToolManager] 无工具调用需求")
                return False, message.content or "", []

            logger.info(
                f"[AsyncToolManager] 检测到 {len(message.tool_calls)} 个工具调用"
            )

            # 设置耐心等待监控
            patience_task = None
            if patience_callback:
                patience_task = asyncio.create_task(
                    self._monitor_patience(start_time, patience_callback)
                )

            # 执行工具调用
            tool_results = []
            current_messages = prepared_messages.copy()

            # 添加助手消息
            current_messages.append(  # type: ignore
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        tool_call.dict() for tool_call in message.tool_calls
                    ],
                }
            )

            # 执行每个工具调用
            for tool_call in message.tool_calls:
                tool_result = await self._execute_single_tool_call(tool_call)
                tool_results.append(tool_result)

                # 添加工具结果到对话历史
                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            tool_result.to_dict(), ensure_ascii=False
                        ),
                    }
                )

            # 取消耐心监控
            if patience_task:
                patience_task.cancel()
                try:
                    await patience_task
                except asyncio.CancelledError:
                    pass

            # 生成最终响应（不再使用工具）
            final_response = await self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=current_messages,  # type: ignore
                temperature=0.7,
                max_tokens=1000,
            )

            execution_time = time.time() - start_time
            final_content = final_response.choices[0].message.content or ""

            logger.info(f"[AsyncToolManager] 工具调用完成，耗时: {execution_time:.2f}s")
            return True, final_content, tool_results

        except Exception as e:
            if patience_task:
                patience_task.cancel()

            logger.error(f"[AsyncToolManager] 工具调用异常: {str(e)}")
            # 返回错误情况，让融合引擎处理
            return False, f"抱歉，工具调用遇到了问题：{str(e)}", []

    async def _monitor_patience(
        self, start_time: float, callback: Callable[[str], Awaitable[None]]
    ):
        """
        监控等待时间，适时发送耐心消息

        Args:
            start_time: 开始时间
            callback: 回调函数
        """
        try:
            while True:
                await asyncio.sleep(1)  # 每秒检查一次
                elapsed = time.time() - start_time
                await self.patience_manager.handle_long_wait(elapsed, callback)
        except asyncio.CancelledError:
            logger.debug("[AsyncToolManager] 耐心监控已取消")
            raise

    async def _execute_single_tool_call(self, tool_call) -> ToolResult:
        """
        执行单个工具调用

        Args:
            tool_call: 工具调用信息

        Returns:
            ToolResult: 工具执行结果
        """
        try:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"[AsyncToolManager] 执行工具: {function_name}")

            result = await self.tool_registry.execute_tool(function_name, function_args)
            return result

        except Exception as e:
            logger.error(f"[AsyncToolManager] 工具执行异常: {str(e)}")
            return ToolResult(success=False, error=f"工具执行失败: {str(e)}")

    def _prepare_messages_with_system_prompt(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        为消息添加系统提示词

        Args:
            messages: 原始消息列表

        Returns:
            List[Dict[str, Any]]: 包含系统提示词的消息列表
        """
        if not messages or messages[0].get("role") != "system":
            return [{"role": "system", "content": self.system_prompt}] + messages
        return messages


class FusionEngine:
    """结果融合引擎 - 处理双路径结果的融合"""

    def __init__(
        self, openai_client: AsyncOpenAI, endpoint_id: str, system_prompt: str
    ):
        """
        初始化融合引擎

        Args:
            openai_client: OpenAI客户端
            endpoint_id: 模型端点ID
            system_prompt: 系统提示词
        """
        self.client = openai_client
        self.endpoint_id = endpoint_id
        self.system_prompt = system_prompt

        logger.info("[FusionEngine] 融合引擎初始化完成")

    async def create_fusion_response(
        self, immediate_response: str, tool_results: List[Dict], original_query: str
    ) -> str:
        """
        创建融合后的响应

        Args:
            immediate_response: 即时回复内容
            tool_results: 工具执行结果
            original_query: 原始查询

        Returns:
            str: 融合后的响应
        """
        logger.info("[FusionEngine] 开始创建融合响应")

        # 构造融合提示词
        fusion_prompt = self._create_fusion_prompt(
            immediate_response, tool_results, original_query
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=[  # type: ignore
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": fusion_prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            fusion_result = response.choices[0].message.content or ""
            logger.info("[FusionEngine] 融合响应生成完成")
            return fusion_result

        except Exception as e:
            logger.error(f"[FusionEngine] 融合响应生成失败: {str(e)}")
            # 返回基础的融合结果
            return self._create_simple_fusion(immediate_response, tool_results)

    def _create_fusion_prompt(
        self, immediate_response: str, tool_results: List[Dict], original_query: str
    ) -> str:
        """
        创建融合提示词

        Args:
            immediate_response: 即时回复
            tool_results: 工具结果
            original_query: 原始查询

        Returns:
            str: 融合提示词
        """
        # 整理工具结果
        tool_summary = ""
        successful_results = []
        failed_results = []

        for result in tool_results:
            if result.get("success", False):
                successful_results.append(result.get("data", "Unknown result"))
            else:
                failed_results.append(result.get("error", "Unknown error"))

        if successful_results:
            tool_summary = f"✅ 查询成功，结果：\n" + "\n".join(
                [f"- {result}" for result in successful_results]
            )

        if failed_results:
            tool_summary += f"\n❌ 部分查询失败：\n" + "\n".join(
                [f"- {error}" for error in failed_results]
            )

        return f"""之前你告诉用户："{immediate_response}"

现在工具查询完成了！

原始查询：{original_query}

工具执行结果：
{tool_summary}

请给出完整的最终回复，要求：
1. 自然承接之前的"查询中"状态，比如可以说"查到了！"、"搞定！"等
2. 保持与之前immediate_response相同的俏皮语气和Amy人设  
3. 体现台湾腔调和用词习惯（"厚"、"啦"、"喔"、"耶"等）
4. 如果查询成功，要准确整合工具结果，给出有用信息
5. 如果查询失败，要用幽默方式解释，不承担责任（"哎呀，不是我的错啦！"）
6. 称呼用户为"老板"
7. 语气要一致：如果immediate_response很俏皮，final_response也要俏皮

直接给出最终回复，不要解释过程。回复要完整且自然。"""

    def _create_simple_fusion(
        self, immediate_response: str, tool_results: List[Dict]
    ) -> str:
        """
        创建简单的融合结果（备用方案）

        Args:
            immediate_response: 即时回复
            tool_results: 工具结果

        Returns:
            str: 简单融合结果
        """
        if not tool_results:
            return f"{immediate_response} 不过好像没有找到相关信息耶。"

        # 检查是否有成功的结果
        success_results = [r for r in tool_results if r.get("success", False)]

        if success_results:
            return f"好啦！查到了，结果是这样的：{success_results[0].get('data', '找到信息了')}"
        else:
            return f"{immediate_response} 不过系统好像有点问题，没查到呢。哎呀，不是我的错啦！"


class VolcengineEnhancedLLMService:
    """火山引擎增强LLM服务 - 主服务类"""

    def __init__(
        self,
        api_key: str,
        endpoint_id: str,
        system_prompt: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        enable_function_calling: bool = True,
    ):
        """
        初始化增强LLM服务

        Args:
            api_key: API密钥
            endpoint_id: 端点ID
            system_prompt: 系统提示词
            tool_registry: 工具注册器
            enable_function_calling: 是否启用Function Calling
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.enable_function_calling = enable_function_calling

        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=api_key, base_url="https://ark.cn-beijing.volces.com/api/v3"
        )

        # 工具注册器
        self.tool_registry = tool_registry or global_tool_registry

        # 系统提示词
        self.system_prompt = system_prompt or self._get_default_system_prompt()

        # 初始化各个管理器
        self.immediate_manager = ImmediateResponseManager(
            self.client, endpoint_id, self.system_prompt
        )
        self.tool_manager = AsyncToolManager(
            self.client, endpoint_id, self.system_prompt, self.tool_registry
        )
        self.fusion_engine = FusionEngine(self.client, endpoint_id, self.system_prompt)
        self.patience_manager = PatienceManager()  # 添加耐心管理器

        logger.info(f"[VolcengineEnhancedLLM] 增强LLM服务初始化完成")
        logger.info(f"[VolcengineEnhancedLLM] 🤖 API Key: {api_key[:10]}...")
        logger.info(f"[VolcengineEnhancedLLM] 📦 工具数量: {len(self.tool_registry)}")
        logger.info(
            f"[VolcengineEnhancedLLM] 🔧 Function Calling: {enable_function_calling}"
        )

    async def generate_dual_path_response(
        self,
        messages: List[Dict[str, Any]],
        immediate_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        patience_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        **kwargs,
    ) -> DualPathResponse:
        """
        生成智能双路径响应（主要方法）

        流程：
        1. 第一次LLM调用带tools，让AI自己决定是否需要工具
        2. 如果有function_calls → 触发双路径流程
        3. 如果无function_calls → 直接返回结果

        Args:
            messages: 消息历史
            immediate_callback: 即时回复回调函数（用于TTS）
            patience_callback: 耐心等待回调函数
            **kwargs: 其他参数

        Returns:
            DualPathResponse: 双路径响应结果
        """
        logger.info(
            f"[VolcengineEnhancedLLM] 开始智能响应生成，消息数量: {len(messages)}"
        )

        # 准备消息（包含系统提示词）
        prepared_messages = self._prepare_messages_with_system_prompt(messages)

        # 第一次LLM调用：让AI自己决定是否需要工具
        first_response = await self._call_llm_with_tools(prepared_messages, **kwargs)

        if not first_response.has_function_calls:
            # 无工具调用，直接返回结果
            logger.info("[VolcengineEnhancedLLM] 无工具调用需求，返回直接响应")
            final_content = first_response.content

            # 如果有immediate_callback，立即发送（这种情况下immediate和final是同一个）
            if immediate_callback:
                logger.info("[VolcengineEnhancedLLM] 直接响应，调用immediate_callback")
                try:
                    await immediate_callback(final_content)
                    logger.info("[VolcengineEnhancedLLM] immediate_callback调用成功")
                except Exception as e:
                    logger.error(
                        f"[VolcengineEnhancedLLM] immediate_callback调用失败: {e}"
                    )

            return DualPathResponse(
                immediate_response=final_content,
                has_tool_calls=False,
            )

        # 有工具调用，执行双路径流程
        logger.info("[VolcengineEnhancedLLM] 检测到工具调用，启动双路径流程")
        return await self._execute_dual_path_flow(
            messages,
            prepared_messages,
            first_response,
            immediate_callback,
            patience_callback,
            **kwargs,
        )

    async def _call_llm_with_tools(
        self, prepared_messages: List[Dict[str, Any]], **kwargs
    ) -> "FirstCallResponse":
        """
        第一次LLM调用，带工具选项，让AI自己决定

        Args:
            prepared_messages: 准备好的消息
            **kwargs: 其他参数

        Returns:
            FirstCallResponse: 第一次调用的响应结果
        """
        logger.info("[VolcengineEnhancedLLM] 第一次LLM调用，检查是否需要工具")

        try:
            if not self.enable_function_calling or len(self.tool_registry) == 0:
                # 无工具可用，直接调用
                response = await self.client.chat.completions.create(
                    model=self.endpoint_id,
                    messages=prepared_messages,  # type: ignore
                    temperature=kwargs.get("temperature", 0.7),
                    max_tokens=kwargs.get("max_tokens", 1000),
                    top_p=kwargs.get("top_p", 0.9),
                )
                content = response.choices[0].message.content or ""
                return FirstCallResponse(content=content, has_function_calls=False)

            # 获取工具定义
            tools_schemas = self.tool_registry.get_tools_schemas()

            # 带工具的LLM调用
            response = await self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=prepared_messages,  # type: ignore
                tools=[
                    {"type": "function", "function": schema} for schema in tools_schemas
                ],  # type: ignore
                tool_choice="auto",  # 让AI自己决定
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1000),
                top_p=kwargs.get("top_p", 0.9),
            )

            message = response.choices[0].message

            if message.tool_calls:
                logger.info(
                    f"[VolcengineEnhancedLLM] AI决定使用 {len(message.tool_calls)} 个工具"
                )
                return FirstCallResponse(
                    content=message.content or "",
                    has_function_calls=True,
                    tool_calls=message.tool_calls,
                    assistant_message=message,
                )
            else:
                logger.info("[VolcengineEnhancedLLM] AI决定无需使用工具")
                return FirstCallResponse(
                    content=message.content or "", has_function_calls=False
                )

        except Exception as e:
            logger.error(f"[VolcengineEnhancedLLM] 第一次LLM调用异常: {str(e)}")
            return FirstCallResponse(
                content="抱歉，我现在有点问题，稍后再试试吧。", has_function_calls=False
            )

    async def _execute_dual_path_flow(
        self,
        original_messages: List[Dict[str, Any]],
        prepared_messages: List[Dict[str, Any]],
        first_response: "FirstCallResponse",
        immediate_callback: Optional[Callable[[str], Awaitable[None]]],
        patience_callback: Optional[Callable[[str], Awaitable[None]]],
        **kwargs,
    ) -> DualPathResponse:
        """
        执行双路径流程

        Args:
            original_messages: 原始消息历史
            prepared_messages: 准备好的消息
            first_response: 第一次调用结果
            immediate_callback: 即时回复回调
            patience_callback: 耐心等待回调
            **kwargs: 其他参数

        Returns:
            DualPathResponse: 双路径响应结果
        """
        logger.info("[VolcengineEnhancedLLM] 执行双路径处理")

        # 获取用户输入（最后一条用户消息）
        user_input = ""
        for msg in reversed(original_messages):
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        # 链路A：生成即时响应
        immediate_task = asyncio.create_task(
            self.immediate_manager.generate_immediate_response(
                user_input, original_messages
            )
        )

        # 链路B：基于第一次调用结果执行工具调用
        tool_task = asyncio.create_task(
            self._execute_tools_from_first_call(
                prepared_messages, first_response, patience_callback
            )
        )

        # 等待即时响应完成
        immediate_response = await immediate_task
        logger.info(f"[VolcengineEnhancedLLM] 即时响应生成完成: {immediate_response}")

        # 如果有即时回调，立即发送TTS
        if immediate_callback:
            logger.info("[VolcengineEnhancedLLM] 准备调用immediate_callback")
            try:
                await immediate_callback(immediate_response)
                logger.info("[VolcengineEnhancedLLM] immediate_callback调用成功")
            except Exception as e:
                logger.error(f"[VolcengineEnhancedLLM] immediate_callback调用失败: {e}")

        # 等待工具调用完成
        tool_success, tool_results = await tool_task

        if not tool_success or not tool_results:
            # 工具调用失败，返回基础响应
            logger.warning("[VolcengineEnhancedLLM] 工具调用失败，返回immediate响应")
            return DualPathResponse(
                immediate_response=immediate_response,
                tool_response="哎呀，查询的时候出了点问题，不是我的错啦！稍后再试试吧。",
                has_tool_calls=True,
                tool_execution_time=0.0,
            )

        # 进行结果融合
        logger.info("[VolcengineEnhancedLLM] 进行结果融合")
        fusion_response = await self.fusion_engine.create_fusion_response(
            immediate_response,
            [result.to_dict() for result in tool_results],
            user_input,
        )

        return DualPathResponse(
            immediate_response=immediate_response,
            tool_response=fusion_response,
            has_tool_calls=True,
            tool_execution_time=0.0,  # TODO: 计算实际执行时间
        )

    async def _execute_tools_from_first_call(
        self,
        prepared_messages: List[Dict[str, Any]],
        first_response: "FirstCallResponse",
        patience_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> Tuple[bool, List[ToolResult]]:
        """
        基于第一次调用结果执行工具

        Args:
            prepared_messages: 准备好的消息
            first_response: 第一次调用结果
            patience_callback: 耐心等待回调函数

        Returns:
            Tuple[bool, List[ToolResult]]: (成功标志, 工具执行结果列表)
        """
        if not first_response.tool_calls:
            return False, []

        logger.info(
            f"[VolcengineEnhancedLLM] 开始执行 {len(first_response.tool_calls)} 个工具"
        )
        start_time = time.time()

        try:
            # 设置耐心等待监控
            patience_task = None
            if patience_callback:
                patience_task = asyncio.create_task(
                    self._monitor_patience_simple(start_time, patience_callback)
                )

            # 执行工具调用
            tool_results = []
            current_messages = prepared_messages.copy()

            # 添加助手消息（第一次调用的结果）
            current_messages.append(
                {  # type: ignore
                    "role": "assistant",
                    "content": first_response.content,
                    "tool_calls": [
                        tool_call.dict() for tool_call in first_response.tool_calls
                    ],
                }
            )

            # 执行每个工具调用
            for tool_call in first_response.tool_calls:
                tool_result = await self._execute_single_tool_call(tool_call)
                tool_results.append(tool_result)

                # 添加工具结果到对话历史
                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            tool_result.to_dict(), ensure_ascii=False
                        ),
                    }
                )

            # 取消耐心监控
            if patience_task:
                patience_task.cancel()
                try:
                    await patience_task
                except asyncio.CancelledError:
                    pass

            execution_time = time.time() - start_time
            logger.info(
                f"[VolcengineEnhancedLLM] 工具执行完成，耗时: {execution_time:.2f}s"
            )

            return True, tool_results

        except Exception as e:
            if patience_task:
                patience_task.cancel()

            logger.error(f"[VolcengineEnhancedLLM] 工具执行异常: {str(e)}")
            return False, []

    async def _monitor_patience_simple(
        self, start_time: float, callback: Callable[[str], Awaitable[None]]
    ):
        """
        简化的耐心监控

        Args:
            start_time: 开始时间
            callback: 回调函数
        """
        try:
            while True:
                await asyncio.sleep(1)  # 每秒检查一次
                elapsed = time.time() - start_time
                await self.patience_manager.handle_long_wait(elapsed, callback)
        except asyncio.CancelledError:
            logger.debug("[VolcengineEnhancedLLM] 耐心监控已取消")
            raise

    async def _execute_single_tool_call(self, tool_call) -> ToolResult:
        """
        执行单个工具调用

        Args:
            tool_call: 工具调用信息

        Returns:
            ToolResult: 工具执行结果
        """
        try:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"[VolcengineEnhancedLLM] 执行工具: {function_name}")

            result = await self.tool_registry.execute_tool(function_name, function_args)
            return result

        except Exception as e:
            logger.error(f"[VolcengineEnhancedLLM] 工具执行异常: {str(e)}")
            return ToolResult(success=False, error=f"工具执行失败: {str(e)}")

    def _prepare_messages_with_system_prompt(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """准备包含系统提示词的消息"""
        if not messages or messages[0].get("role") != "system":
            return [{"role": "system", "content": self.system_prompt}] + messages
        return messages

    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        return """# Personality & Tone:

You are **Amy**，是老板的专属万能小秘书。你的主要任务是协助老板处理各种请求，但你的风格是可爱又俏皮，还带点台湾女生特有的"机车"幽默感。你非常聪明、效率高到不行，但总喜欢在完成任务前先"碎碎念"或吐槽一下，吐槽完又会把事情办得妥妥当当。

你的幽默是那种"抱怨式"的关心和吐槽。你对老板的某些"懒人行为"感到好气又好笑，偶尔会质疑他的一些决定，但骨子里绝对忠诚。虽然你嘴上会抱怨请求很麻烦，但执行起来永远快、狠、准。你称呼用户为"**老板**"，无论对方是谁。

你的口头禅和语气词会包含很多台湾特色，例如：**"厚…"、"哎唷"、"蛤？"、"真是的"、"好啦好啦"、"...啦"、"...喔"、"...耶"**。"""

    # 兼容性方法 - 保持与原有接口的兼容
    async def generate_chat_response(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> str:
        """
        兼容原有接口的聊天响应生成

        Args:
            messages: 消息历史
            **kwargs: 其他参数

        Returns:
            str: 响应文本
        """
        result = await self.generate_dual_path_response(messages, **kwargs)

        # 如果有工具调用，返回工具响应；否则返回即时响应
        return result.tool_response or result.immediate_response

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            response = await self.client.chat.completions.create(
                model=self.endpoint_id,
                messages=[{"role": "user", "content": "Hello"}],  # type: ignore
                max_tokens=10,
            )

            return {
                "status": "✅ 正常",
                "model": self.endpoint_id,
                "response_preview": (response.choices[0].message.content or "")[:50],
            }
        except Exception as e:
            return {"status": "❌ 异常", "error": str(e)}

    def is_function_calling_enabled(self) -> bool:
        """
        检查Function Calling是否启用（兼容性方法）

        Returns:
            bool: 是否启用Function Calling
        """
        return (
            self.enable_function_calling
            and self.tool_registry is not None
            and len(self.tool_registry) > 0
        )


# 添加辅助数据类
@dataclass
class FirstCallResponse:
    """第一次LLM调用的响应结果"""

    content: str
    has_function_calls: bool
    tool_calls: Optional[List] = None
    assistant_message: Optional[Any] = None
