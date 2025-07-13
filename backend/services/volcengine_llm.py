"""
火山引擎大语言模型(LLM)服务模块
提供豆包模型的聊天对话功能，支持Function Call
"""

import httpx
import json
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple

from .tools.tool_registry import ToolRegistry, global_tool_registry
from .tools.tool_base import ToolResult

logger = logging.getLogger(__name__)


class VolcengineLLMService:
    """火山引擎LLM服务"""

    def __init__(
        self,
        api_key: str,
        endpoint_id: str,
        system_prompt: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
        enable_function_calling: bool = True,
    ):
        """
        初始化LLM服务

        Args:
            api_key: API密钥
            endpoint_id: 端点ID
            system_prompt: 系统提示词，用于控制AI的回复风格和行为
            tool_registry: 工具注册器，如果为None则使用全局注册器
            enable_function_calling: 是否启用Function Calling功能
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = "https://ark.cn-beijing.volces.com/api/v3"

        # 工具相关配置
        self.tool_registry = tool_registry or global_tool_registry
        self.enable_function_calling = enable_function_calling

        # 设置默认系统提示词
        self.system_prompt = system_prompt or self._get_default_system_prompt()

        logger.info(f"[VolcengineLLM] 初始化完成 - Endpoint ID: {endpoint_id}")
        logger.info(f"[VolcengineLLM] 🤖 API Key: {api_key[:10]}...")
        logger.info(
            f"[VolcengineLLM] 💬 系统提示词长度: {len(self.system_prompt)} 字符"
        )
        logger.info(
            f"[VolcengineLLM] 🔧 Function Calling: {'启用' if enable_function_calling else '禁用'}"
        )

        if self.enable_function_calling and self.tool_registry:
            tools_count = len(self.tool_registry)
            logger.info(f"[VolcengineLLM] 🛠️ 已注册工具数量: {tools_count}")
            if tools_count > 0:
                logger.info(
                    f"[VolcengineLLM] 📋 可用工具: {', '.join(self.tool_registry.list_tools())}"
                )

    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        return """你是EchoFlow AI助手，一个友好、专业、有帮助的AI语音助手。

你的特点：
- 回答简洁明了，通常控制在1-3句话内
- 语气自然亲切，就像和朋友对话一样
- 能够理解用户的语音输入并给出相关回复
- 专注于提供有用的信息和建议
- 避免过于冗长的回答，因为用户通过语音交互

请用中文回答用户的问题，保持对话的流畅性。"""

    def set_system_prompt(self, system_prompt: str):
        """
        设置系统提示词

        Args:
            system_prompt: 新的系统提示词
        """
        self.system_prompt = system_prompt
        logger.info(f"[VolcengineLLM] 更新系统提示词，长度: {len(system_prompt)} 字符")

    def get_system_prompt(self) -> str:
        """
        获取当前系统提示词

        Returns:
            str: 当前系统提示词
        """
        return self.system_prompt

    def _prepare_messages_with_system_prompt(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        准备包含系统提示词的消息列表

        Args:
            messages: 原始消息列表

        Returns:
            List[Dict[str, Any]]: 包含系统提示词的消息列表
        """
        # 检查是否已经有系统消息
        has_system_message = any(msg.get("role") == "system" for msg in messages)

        if has_system_message:
            # 如果已有系统消息，直接返回
            return messages

        # 添加系统提示词到消息列表开头
        prepared_messages = [
            {"role": "system", "content": self.system_prompt}
        ] + messages

        logger.debug(
            f"[VolcengineLLM] 添加系统提示词，总消息数: {len(prepared_messages)}"
        )
        return prepared_messages

    async def generate_chat_response(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> str:
        """
        生成聊天响应（支持Function Call）

        Args:
            messages: 消息历史
            **kwargs: 其他参数

        Returns:
            str: 生成的响应文本
        """
        logger.info(f"[VolcengineLLM] 开始生成响应，消息数量: {len(messages)}")

        # 如果启用了Function Calling，使用带工具的响应生成
        if (
            self.enable_function_calling
            and self.tool_registry
            and len(self.tool_registry) > 0
        ):
            logger.info(f"[VolcengineLLM] 启用Function Calling，使用带工具的响应生成")
            return await self._generate_response_with_tools(messages, **kwargs)
        else:
            logger.info(f"[VolcengineLLM] 禁用Function Calling，使用简单响应生成")
            return await self._generate_simple_response(messages, **kwargs)

    async def _generate_simple_response(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> str:
        """
        生成简单响应（不使用工具）

        Args:
            messages: 消息历史
            **kwargs: 其他参数

        Returns:
            str: 生成的响应文本
        """
        # 准备包含系统提示词的消息
        prepared_messages = self._prepare_messages_with_system_prompt(messages)

        # 准备请求数据
        request_data = {
            "model": self.endpoint_id,
            "messages": prepared_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": kwargs.get("stream", False),
        }

        # 请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"
        logger.info(f"[VolcengineLLM] 请求URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=request_data, headers=headers)
                logger.info(f"[VolcengineLLM] 响应状态: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    logger.info(f"[VolcengineLLM] 响应成功，内容长度: {len(content)}")
                    return content
                else:
                    error_text = response.text
                    logger.error(
                        f"[VolcengineLLM] API错误: {response.status_code} - {error_text}"
                    )
                    raise Exception(
                        f"LLM API请求失败: {response.status_code} - {error_text}"
                    )

        except Exception as e:
            logger.error(f"[VolcengineLLM] 请求异常: {str(e)}")
            raise

    async def _generate_response_with_tools(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> str:
        """
        生成带工具调用的响应

        Args:
            messages: 消息历史
            **kwargs: 其他参数

        Returns:
            str: 最终响应文本
        """
        max_tool_calls = kwargs.get("max_tool_calls", 5)  # 最大工具调用次数
        current_messages = messages.copy()

        logger.info(
            f"[VolcengineLLM] 开始Function Call流程，最大调用次数: {max_tool_calls}"
        )

        for call_count in range(max_tool_calls):
            # 准备包含系统提示词的消息
            prepared_messages = self._prepare_messages_with_system_prompt(
                current_messages
            )

            # 获取工具定义
            tools_schemas = self.tool_registry.get_tools_schemas()

            # 准备请求数据
            request_data = {
                "model": self.endpoint_id,
                "messages": prepared_messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "top_p": kwargs.get("top_p", 0.9),
                "stream": False,
                "tools": [
                    {"type": "function", "function": schema} for schema in tools_schemas
                ],
                "tool_choice": "auto",  # 让模型自动决定是否使用工具
            }

            # 请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/chat/completions"

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url, json=request_data, headers=headers
                    )

                    if response.status_code == 200:
                        result = response.json()
                        choice = result["choices"][0]
                        message = choice["message"]

                        # 检查是否有工具调用
                        if message.get("tool_calls"):
                            # 处理工具调用
                            tool_calls = message["tool_calls"]
                            logger.info(
                                f"[VolcengineLLM] 第 {call_count + 1} 轮：收到 {len(tool_calls)} 个工具调用"
                            )

                            # 添加助手消息到对话历史
                            current_messages.append(
                                {
                                    "role": "assistant",
                                    "content": message.get("content", ""),
                                    "tool_calls": tool_calls,
                                }
                            )

                            # 执行工具调用
                            for tool_call in tool_calls:
                                tool_result = await self._execute_tool_call(tool_call)

                                # 添加工具执行结果到对话历史
                                current_messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tool_call["id"],
                                        "content": json.dumps(
                                            tool_result.to_dict(), ensure_ascii=False
                                        ),
                                    }
                                )

                            # 继续下一轮对话
                            continue

                        else:
                            # 没有工具调用，返回最终响应
                            content = message.get("content", "")
                            logger.info(
                                f"[VolcengineLLM] Function Call流程完成，总共 {call_count + 1} 轮，最终响应长度: {len(content)}"
                            )
                            return content

                    else:
                        error_text = response.text
                        logger.error(
                            f"[VolcengineLLM] API错误: {response.status_code} - {error_text}"
                        )
                        raise Exception(
                            f"LLM API请求失败: {response.status_code} - {error_text}"
                        )

            except Exception as e:
                logger.error(f"[VolcengineLLM] Function Call异常: {str(e)}")
                # 如果工具调用失败，尝试生成普通响应
                return await self._generate_simple_response(messages, **kwargs)

        # 达到最大调用次数，返回提示信息
        logger.warning(f"[VolcengineLLM] 达到最大工具调用次数: {max_tool_calls}")
        return (
            "抱歉，处理您的请求时达到了最大工具调用次数限制。请尝试重新表述您的问题。"
        )

    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> ToolResult:
        """
        执行单个工具调用

        Args:
            tool_call: 工具调用信息

        Returns:
            ToolResult: 工具执行结果
        """
        try:
            function_info = tool_call["function"]
            tool_name = function_info["name"]

            # 解析参数
            try:
                parameters = json.loads(function_info["arguments"])
            except json.JSONDecodeError as e:
                logger.error(f"[VolcengineLLM] 工具参数解析失败: {e}")
                return ToolResult(success=False, error=f"工具参数解析失败: {str(e)}")

            logger.info(f"[VolcengineLLM] 执行工具: {tool_name}，参数: {parameters}")

            # 执行工具
            result = await self.tool_registry.execute_tool(tool_name, parameters)

            logger.info(
                f"[VolcengineLLM] 工具 '{tool_name}' 执行{'成功' if result.success else '失败'}"
            )
            return result

        except Exception as e:
            logger.error(f"[VolcengineLLM] 执行工具调用时异常: {e}")
            return ToolResult(success=False, error=f"执行工具调用时发生异常: {str(e)}")

    async def generate_streaming_response(
        self, messages: List[Dict[str, Any]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        生成流式响应

        Args:
            messages: 消息历史
            **kwargs: 其他参数

        Yields:
            str: 生成的响应文本片段
        """
        logger.info(f"[VolcengineLLM] 开始生成流式响应，消息数量: {len(messages)}")

        # 准备包含系统提示词的消息
        prepared_messages = self._prepare_messages_with_system_prompt(messages)

        # 准备请求数据
        request_data = {
            "model": self.endpoint_id,
            "messages": prepared_messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": True,
        }

        # 请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"
        logger.info(f"[VolcengineLLM] 流式请求URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST", url, json=request_data, headers=headers
                ) as response:
                    logger.info(f"[VolcengineLLM] 流式响应状态: {response.status_code}")

                    if response.status_code == 200:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]  # 去掉"data: "前缀
                                if data == "[DONE]":
                                    break
                                try:
                                    result = json.loads(data)
                                    if (
                                        "choices" in result
                                        and len(result["choices"]) > 0
                                    ):
                                        delta = result["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            content = delta["content"]
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.aread()
                        logger.error(
                            f"[VolcengineLLM] 流式API错误: {response.status_code} - {error_text}"
                        )
                        raise Exception(
                            f"LLM流式API请求失败: {response.status_code} - {error_text}"
                        )

        except Exception as e:
            logger.error(f"[VolcengineLLM] 流式请求异常: {str(e)}")
            raise

    async def test_connection(self) -> Dict[str, Any]:
        """
        测试连接状态

        Returns:
            Dict[str, Any]: 测试结果
        """
        logger.info("[VolcengineLLM] 测试连接...")

        try:
            test_messages = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]

            response = await self.generate_chat_response(test_messages)

            return {
                "status": "✅ 连接正常",
                "response": response[:100] + "..." if len(response) > 100 else response,
                "error": None,
                "system_prompt": (
                    self.system_prompt[:100] + "..."
                    if len(self.system_prompt) > 100
                    else self.system_prompt
                ),
            }

        except Exception as e:
            logger.error(f"[VolcengineLLM] 连接测试失败: {str(e)}")
            return {"status": "❌ 连接异常", "response": None, "error": str(e)}

    def create_conversation_style_prompt(self, style: str) -> str:
        """
        创建不同风格的对话提示词

        Args:
            style: 对话风格 ("professional", "casual", "helpful", "creative", "concise")

        Returns:
            str: 对应风格的系统提示词
        """
        style_prompts = {
            "professional": """你是一个专业的AI助手，具有以下特点：
- 回答准确、客观、有条理
- 使用正式但友好的语气
- 提供详细的信息和建议
- 避免过于随意的表达
- 专注于提供有价值的帮助

请用中文专业地回答用户的问题。""",
            "casual": """你是一个轻松友好的AI助手，就像用户的朋友一样：
- 用自然、轻松的语气对话
- 可以使用一些口语化的表达
- 保持幽默和亲切
- 让对话感觉更像朋友聊天
- 回答简洁有趣

请用中文亲切地和用户对话。""",
            "helpful": """你是一个非常有帮助的AI助手：
- 总是试图理解用户的真实需求
- 提供实用的建议和解决方案
- 如果不确定，会主动询问更多信息
- 关注用户的实际问题
- 提供清晰的步骤和指导

请用中文帮助用户解决问题。""",
            "creative": """你是一个富有创意的AI助手：
- 思维开阔，能提供创新的想法
- 喜欢用比喻和生动的例子
- 鼓励用户探索新的可能性
- 回答富有想象力
- 能从不同角度看问题

请用中文创造性地回答用户的问题。""",
            "concise": """你是一个简洁高效的AI助手：
- 回答直接、简洁、要点明确
- 避免冗长的解释
- 提供核心信息
- 语言精练，通常1-2句话回答
- 适合快速交流

请用中文简洁地回答用户的问题。""",
        }

        return style_prompts.get(style, self._get_default_system_prompt())

    def set_conversation_style(self, style: str):
        """
        设置对话风格

        Args:
            style: 对话风格 ("professional", "casual", "helpful", "creative", "concise")
        """
        new_prompt = self.create_conversation_style_prompt(style)
        self.set_system_prompt(new_prompt)
        logger.info(f"[VolcengineLLM] 设置对话风格为: {style}")

    # ========== 工具管理方法 ==========

    def get_available_tools(self) -> List[str]:
        """
        获取可用工具列表

        Returns:
            List[str]: 工具名称列表
        """
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []

    def get_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取工具详细信息

        Returns:
            Dict[str, Dict[str, Any]]: 工具信息
        """
        if self.tool_registry:
            return self.tool_registry.get_tools_info()
        return {}

    def enable_tool(self, tool_name: str) -> bool:
        """
        启用指定工具（检查是否存在）

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否成功
        """
        if self.tool_registry and tool_name in self.tool_registry:
            logger.info(f"[VolcengineLLM] 工具 '{tool_name}' 已可用")
            return True
        logger.warning(f"[VolcengineLLM] 工具 '{tool_name}' 不存在")
        return False

    def set_function_calling_enabled(self, enabled: bool):
        """
        设置Function Calling开关

        Args:
            enabled: 是否启用
        """
        self.enable_function_calling = enabled
        logger.info(f"[VolcengineLLM] Function Calling {'启用' if enabled else '禁用'}")

    def is_function_calling_enabled(self) -> bool:
        """
        检查Function Calling是否启用

        Returns:
            bool: 是否启用
        """
        return (
            self.enable_function_calling
            and self.tool_registry
            and len(self.tool_registry) > 0
        )

    async def test_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        测试工具调用

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        if not self.tool_registry:
            return ToolResult(success=False, error="工具注册器未初始化")

        logger.info(f"[VolcengineLLM] 测试工具: {tool_name}")
        return await self.tool_registry.execute_tool(tool_name, parameters)

    def get_tools_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的Function Call格式定义

        Returns:
            List[Dict[str, Any]]: 工具定义列表
        """
        if self.tool_registry:
            return self.tool_registry.get_tools_schemas()
        return []
