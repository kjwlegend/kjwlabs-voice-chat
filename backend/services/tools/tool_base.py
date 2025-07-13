"""
工具基类和相关数据结构
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ParameterType(Enum):
    """参数类型枚举"""

    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """工具参数定义"""

    name: str  # 参数名称
    type: ParameterType  # 参数类型
    description: str  # 参数描述
    required: bool = False  # 是否必需
    default: Optional[Any] = None  # 默认值
    enum: Optional[List[Any]] = None  # 枚举值列表
    pattern: Optional[str] = None  # 正则表达式模式（对字符串类型）
    minimum: Optional[Union[int, float]] = None  # 最小值（对数字类型）
    maximum: Optional[Union[int, float]] = None  # 最大值（对数字类型）
    items: Optional[Dict[str, Any]] = None  # 数组项定义（对数组类型）

    def to_json_schema(self) -> Dict[str, Any]:
        """转换为JSON Schema格式"""
        schema = {"type": self.type.value, "description": self.description}

        if self.enum:
            schema["enum"] = self.enum
        if self.pattern and self.type == ParameterType.STRING:
            schema["pattern"] = self.pattern
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.items and self.type == ParameterType.ARRAY:
            schema["items"] = self.items
        if self.default is not None:
            schema["default"] = self.default

        return schema


@dataclass
class ToolResult:
    """工具执行结果"""

    success: bool  # 是否成功
    data: Optional[Any] = None  # 返回数据
    error: Optional[str] = None  # 错误信息
    execution_time: Optional[float] = None  # 执行时间（秒）
    metadata: Optional[Dict[str, Any]] = None  # 元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"success": self.success, "data": self.data, "error": self.error}

        if self.execution_time is not None:
            result["execution_time"] = self.execution_time
        if self.metadata:
            result["metadata"] = self.metadata

        return result


class ToolBase(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str):
        """
        初始化工具

        Args:
            name: 工具名称
            description: 工具描述
        """
        self.name = name
        self.description = description
        self.parameters: List[ToolParameter] = []

        logger.info(f"[Tool] 初始化工具: {name}")

    def add_parameter(self, parameter: ToolParameter) -> "ToolBase":
        """
        添加参数

        Args:
            parameter: 工具参数

        Returns:
            ToolBase: 返回自身，支持链式调用
        """
        self.parameters.append(parameter)
        logger.debug(f"[Tool:{self.name}] 添加参数: {parameter.name}")
        return self

    def get_function_schema(self) -> Dict[str, Any]:
        """
        获取Function Call格式的工具定义

        Returns:
            Dict[str, Any]: Function Call格式的工具定义
        """
        properties = {}
        required_params = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required_params.append(param.name)

        schema = {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": properties},
        }

        if required_params:
            schema["parameters"]["required"] = required_params

        return schema

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        验证参数

        Args:
            parameters: 参数字典

        Returns:
            bool: 是否验证通过
        """
        try:
            # 检查必需参数
            for param in self.parameters:
                if param.required and param.name not in parameters:
                    logger.error(f"[Tool:{self.name}] 缺少必需参数: {param.name}")
                    return False

            # 检查参数类型和值
            for param_name, param_value in parameters.items():
                param_def = next(
                    (p for p in self.parameters if p.name == param_name), None
                )
                if param_def:
                    if not self._validate_parameter_value(param_def, param_value):
                        return False

            return True

        except Exception as e:
            logger.error(f"[Tool:{self.name}] 参数验证异常: {e}")
            return False

    def _validate_parameter_value(self, param: ToolParameter, value: Any) -> bool:
        """验证单个参数值"""
        try:
            # 类型检查
            if param.type == ParameterType.STRING and not isinstance(value, str):
                logger.error(f"[Tool:{self.name}] 参数 {param.name} 应为字符串类型")
                return False
            elif param.type == ParameterType.INTEGER and not isinstance(value, int):
                logger.error(f"[Tool:{self.name}] 参数 {param.name} 应为整数类型")
                return False
            elif param.type == ParameterType.NUMBER and not isinstance(
                value, (int, float)
            ):
                logger.error(f"[Tool:{self.name}] 参数 {param.name} 应为数字类型")
                return False
            elif param.type == ParameterType.BOOLEAN and not isinstance(value, bool):
                logger.error(f"[Tool:{self.name}] 参数 {param.name} 应为布尔类型")
                return False
            elif param.type == ParameterType.ARRAY and not isinstance(value, list):
                logger.error(f"[Tool:{self.name}] 参数 {param.name} 应为数组类型")
                return False
            elif param.type == ParameterType.OBJECT and not isinstance(value, dict):
                logger.error(f"[Tool:{self.name}] 参数 {param.name} 应为对象类型")
                return False

            # 枚举值检查
            if param.enum and value not in param.enum:
                logger.error(
                    f"[Tool:{self.name}] 参数 {param.name} 值不在枚举列表中: {param.enum}"
                )
                return False

            # 数值范围检查
            if param.type in [ParameterType.INTEGER, ParameterType.NUMBER]:
                if param.minimum is not None and value < param.minimum:
                    logger.error(
                        f"[Tool:{self.name}] 参数 {param.name} 值小于最小值: {param.minimum}"
                    )
                    return False
                if param.maximum is not None and value > param.maximum:
                    logger.error(
                        f"[Tool:{self.name}] 参数 {param.name} 值大于最大值: {param.maximum}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"[Tool:{self.name}] 参数值验证异常: {e}")
            return False

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        执行工具

        Args:
            parameters: 参数字典

        Returns:
            ToolResult: 执行结果
        """
        pass

    async def safe_execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """
        安全执行工具（包含参数验证和异常处理）

        Args:
            parameters: 参数字典

        Returns:
            ToolResult: 执行结果
        """
        import time

        start_time = time.time()

        try:
            logger.info(f"[Tool:{self.name}] 开始执行，参数: {parameters}")

            # 参数验证
            if not self.validate_parameters(parameters):
                return ToolResult(
                    success=False,
                    error="参数验证失败",
                    execution_time=time.time() - start_time,
                )

            # 执行工具
            result = await self.execute(parameters)
            result.execution_time = time.time() - start_time

            logger.info(
                f"[Tool:{self.name}] 执行完成，耗时: {result.execution_time:.2f}s，成功: {result.success}"
            )
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"[Tool:{self.name}] 执行异常: {e}")
            return ToolResult(
                success=False,
                error=f"工具执行异常: {str(e)}",
                execution_time=execution_time,
            )
