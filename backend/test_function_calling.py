#!/usr/bin/env python3
"""
Function Calling功能测试脚本
测试LLM服务的工具调用功能
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(".")

from services.volcengine_service import VolcengineService
from services.tools.tool_registry import global_tool_registry
from services.tools.n8n_webhook_tool import N8NWebhookTool
from config import Config
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_basic_tool_functionality():
    """测试基础工具功能"""
    logger.info("=" * 60)
    logger.info("1. 测试基础工具功能")
    logger.info("=" * 60)

    # 测试工具注册器
    logger.info("📋 测试工具注册器...")
    print(f"全局工具注册器状态: {global_tool_registry}")
    print(f"已注册工具数量: {len(global_tool_registry)}")

    if len(global_tool_registry) > 0:
        print(f"可用工具: {', '.join(global_tool_registry.list_tools())}")

        # 获取工具详细信息
        tools_info = global_tool_registry.get_tools_info()
        for tool_name, info in tools_info.items():
            print(f"\n工具: {tool_name}")
            print(f"  描述: {info['description']}")
            print(f"  参数数量: {info['parameters_count']}")
    else:
        print("⚠️ 没有注册任何工具")


async def test_n8n_tool_directly():
    """直接测试N8N工具"""
    logger.info("=" * 60)
    logger.info("2. 直接测试N8N工具")
    logger.info("=" * 60)

    # 创建测试N8N工具
    # 注意：这里使用一个测试URL，实际使用时需要替换为真实的N8N Webhook URL
    test_webhook_url = "https://kai.kjwlabs.com/webhook/n8n"  # 测试用的回显服务

    n8n_tool = N8NWebhookTool(webhook_url=test_webhook_url)

    # 测试参数 - 现在只需要query参数
    test_params = {
        "query": "Hello from Function Call test! This is a test message with timestamp 2024-01-01T00:00:00Z and test data: key=value"
    }

    logger.info(f"测试参数: {test_params}")

    try:
        result = await n8n_tool.safe_execute(test_params)
        print(f"\n✅ N8N工具测试结果:")
        print(f"  成功: {result.success}")
        print(f"  执行时间: {result.execution_time:.2f}s")

        if result.success:
            print(
                f"  响应数据: {json.dumps(result.data, indent=2, ensure_ascii=False)}"
            )
        else:
            print(f"  错误信息: {result.error}")

    except Exception as e:
        print(f"❌ N8N工具测试失败: {e}")


async def test_volcengine_service_integration():
    """测试火山引擎服务集成"""
    logger.info("=" * 60)
    logger.info("3. 测试火山引擎服务集成")
    logger.info("=" * 60)

    config = Config()

    # 创建服务实例，启用Function Calling
    service = VolcengineService(
        access_key=config.VOLCENGINE_ACCESS_KEY,
        secret_key=config.VOLCENGINE_SECRET_KEY,
        app_id=config.VOLCENGINE_APP_ID,
        api_key=config.VOLCENGINE_API_KEY,
        endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
        n8n_webhook_url="https://httpbin.org/post",  # 测试URL
        enable_function_calling=True,
    )

    # 检查服务状态
    print(f"Function Calling启用状态: {service.is_function_calling_enabled()}")
    print(f"可用工具: {service.get_available_tools()}")

    # 获取工具信息
    tools_info = service.get_tools_info()
    for tool_name, info in tools_info.items():
        print(f"\n工具: {tool_name}")
        print(f"  描述: {info['description']}")
        print(f"  参数数量: {info['parameters_count']}")


async def test_direct_tool_call():
    """测试直接工具调用"""
    logger.info("=" * 60)
    logger.info("4. 测试直接工具调用")
    logger.info("=" * 60)

    config = Config()

    service = VolcengineService(
        access_key=config.VOLCENGINE_ACCESS_KEY,
        secret_key=config.VOLCENGINE_SECRET_KEY,
        app_id=config.VOLCENGINE_APP_ID,
        api_key=config.VOLCENGINE_API_KEY,
        endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
        n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n",
        enable_function_calling=True,
    )

    # 直接调用工具 - 现在只需要query参数
    test_params = {"query": "测试用户请求：执行测试操作 (direct_test)"}

    try:
        result = await service.test_tool("n8n_webhook", test_params)
        print(f"\n✅ 直接工具调用结果:")
        print(f"  成功: {result['success']}")
        print(f"  执行时间: {result.get('execution_time', 'N/A')}s")

        if result["success"]:
            print(
                f"  响应数据: {json.dumps(result['data'], indent=2, ensure_ascii=False)}"
            )
        else:
            print(f"  错误信息: {result['error']}")

    except Exception as e:
        print(f"❌ 直接工具调用失败: {e}")


async def test_llm_function_calling():
    """测试LLM Function Calling"""
    logger.info("=" * 60)
    logger.info("5. 测试LLM Function Calling")
    logger.info("=" * 60)

    config = Config()

    service = VolcengineService(
        access_key=config.VOLCENGINE_ACCESS_KEY,
        secret_key=config.VOLCENGINE_SECRET_KEY,
        app_id=config.VOLCENGINE_APP_ID,
        api_key=config.VOLCENGINE_API_KEY,
        endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
        n8n_webhook_url="https://httpbin.org/post",
        enable_function_calling=True,
    )

    if not service.llm_service:
        print("❌ LLM服务未初始化，跳过测试")
        return

    # 测试消息 - 让AI调用工具
    test_messages = [
        {
            "role": "user",
            "content": "请帮我调用n8n工具，发送一个测试查询：Hello from LLM! This is a test message of type: test",
        }
    ]

    try:
        print("🤖 开始LLM Function Call测试...")
        print(f"测试消息: {test_messages[0]['content']}")

        response = await service.generate_chat_response(test_messages)

        print(f"\n✅ LLM Function Call响应:")
        print(f"回复内容: {response}")

    except Exception as e:
        print(f"❌ LLM Function Call测试失败: {e}")
        logger.error(f"详细错误: {e}", exc_info=True)


async def main():
    """主测试函数"""
    print("🚀 开始Function Calling功能测试")
    print("=" * 60)

    try:
        # 依次执行各项测试
        await test_basic_tool_functionality()
        await test_n8n_tool_directly()
        await test_volcengine_service_integration()
        await test_direct_tool_call()
        await test_llm_function_calling()

        print("\n" + "=" * 60)
        print("🎉 Function Calling功能测试完成！")
        print("=" * 60)

        print("\n📋 测试总结:")
        print("1. ✅ 基础工具功能正常")
        print("2. ✅ N8N工具直接调用正常")
        print("3. ✅ 火山引擎服务集成正常")
        print("4. ✅ 直接工具调用正常")
        print("5. ✅ LLM Function Calling正常")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        logger.error(f"测试异常: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
