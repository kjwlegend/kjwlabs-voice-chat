"""
工具注册器
管理和注册所有可用的LLM工具
"""

from typing import Dict, List, Any, Optional
import logging

from .tool_base import ToolBase, ToolResult
from .n8n_webhook_tool import N8NWebhookTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册器"""

    def __init__(self):
        """初始化工具注册器"""
        self.tools: Dict[str, ToolBase] = {}
        self._initialized = False

        logger.info("[ToolRegistry] 初始化工具注册器")

    def register_tool(self, tool: ToolBase) -> "ToolRegistry":
        """
        注册工具

        Args:
            tool: 要注册的工具

        Returns:
            ToolRegistry: 返回自身，支持链式调用
        """
        if tool.name in self.tools:
            logger.warning(f"[ToolRegistry] 工具 '{tool.name}' 已存在，将被覆盖")

        self.tools[tool.name] = tool
        logger.info(f"[ToolRegistry] 注册工具: {tool.name} - {tool.description}")
        return self

    def unregister_tool(self, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否成功注销
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"[ToolRegistry] 注销工具: {tool_name}")
            return True
        else:
            logger.warning(f"[ToolRegistry] 工具 '{tool_name}' 不存在，无法注销")
            return False

    def get_tool(self, tool_name: str) -> Optional[ToolBase]:
        """
        获取工具

        Args:
            tool_name: 工具名称

        Returns:
            Optional[ToolBase]: 工具实例，如果不存在则返回None
        """
        return self.tools.get(tool_name)

    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具名称

        Returns:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())

    def get_tools_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的Function Call格式定义

        Returns:
            List[Dict[str, Any]]: 工具定义列表
        """
        schemas = []
        for tool in self.tools.values():
            try:
                schema = tool.get_function_schema()
                schemas.append(schema)
                logger.debug(f"[ToolRegistry] 获取工具 '{tool.name}' 的schema成功")
            except Exception as e:
                logger.error(f"[ToolRegistry] 获取工具 '{tool.name}' 的schema失败: {e}")

        return schemas

    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定工具的Function Call格式定义

        Args:
            tool_name: 工具名称

        Returns:
            Optional[Dict[str, Any]]: 工具定义，如果不存在则返回None
        """
        tool = self.get_tool(tool_name)
        if tool:
            try:
                return tool.get_function_schema()
            except Exception as e:
                logger.error(f"[ToolRegistry] 获取工具 '{tool_name}' 的schema失败: {e}")
                return None
        return None

    async def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> ToolResult:
        """
        执行工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"[ToolRegistry] 工具 '{tool_name}' 不存在")
            return ToolResult(success=False, error=f"工具 '{tool_name}' 不存在")

        try:
            logger.info(f"[ToolRegistry] 执行工具: {tool_name}")
            result = await tool.safe_execute(parameters)
            logger.info(f"[ToolRegistry] 工具 '{tool_name}' 执行完成: {result.success}")
            return result
        except Exception as e:
            logger.error(f"[ToolRegistry] 执行工具 '{tool_name}' 时发生异常: {e}")
            return ToolResult(success=False, error=f"执行工具时发生异常: {str(e)}")

    def get_tools_info(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有工具的详细信息

        Returns:
            Dict[str, Dict[str, Any]]: 工具信息字典
        """
        tools_info = {}
        for name, tool in self.tools.items():
            tools_info[name] = {
                "name": tool.name,
                "description": tool.description,
                "parameters_count": len(tool.parameters),
                "schema": tool.get_function_schema(),
            }
        return tools_info

    def initialize_default_tools(
        self,
        n8n_webhook_url: Optional[str] = None,
        n8n_timeout: int = 30,
    ) -> "ToolRegistry":
        """
        初始化默认工具集

        Args:
            n8n_webhook_url: N8N Webhook URL
            n8n_timeout: N8N请求超时时间

        Returns:
            ToolRegistry: 返回自身，支持链式调用
        """
        if self._initialized:
            logger.warning("[ToolRegistry] 默认工具已初始化，跳过重复初始化")
            return self

        logger.info("[ToolRegistry] 开始初始化默认工具集...")

        try:
            # 注册N8N Webhook工具
            n8n_tool = N8NWebhookTool(
                webhook_url=n8n_webhook_url,
                timeout=n8n_timeout,
            )
            self.register_tool(n8n_tool)

            # 这里可以注册更多默认工具
            # 例如：
            # self.register_tool(WeatherTool())
            # self.register_tool(EmailTool())
            # self.register_tool(DatabaseTool())

            self._initialized = True
            logger.info(
                f"[ToolRegistry] 默认工具集初始化完成，共注册 {len(self.tools)} 个工具"
            )

        except Exception as e:
            logger.error(f"[ToolRegistry] 初始化默认工具集失败: {e}")
            raise

        return self

    def is_initialized(self) -> bool:
        """
        检查是否已初始化

        Returns:
            bool: 是否已初始化
        """
        return self._initialized

    def clear_tools(self):
        """清空所有工具"""
        tool_count = len(self.tools)
        self.tools.clear()
        self._initialized = False
        logger.info(f"[ToolRegistry] 清空所有工具，共清除 {tool_count} 个工具")

    def __len__(self) -> int:
        """返回已注册工具的数量"""
        return len(self.tools)

    def __contains__(self, tool_name: str) -> bool:
        """检查工具是否已注册"""
        return tool_name in self.tools

    def __iter__(self):
        """支持迭代"""
        return iter(self.tools.values())

    def __str__(self) -> str:
        """字符串表示"""
        return f"ToolRegistry(tools_count={len(self.tools)}, tools={list(self.tools.keys())})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return self.__str__()


# 全局工具注册器实例
global_tool_registry = ToolRegistry()
