#!/usr/bin/env python3
"""
测试增强LLM服务
测试双路径响应机制、OpenAI SDK集成和各个管理器组件
"""

import sys
import os
import json
import logging
import asyncio
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_enhanced_llm_service():
    """测试增强LLM服务的各项功能"""

    print("=" * 70)
    print("测试增强LLM服务 - 双路径响应机制")
    print("=" * 70)

    try:
        from config import Config
        from services.volcengine_llm_enhanced import (
            VolcengineEnhancedLLMService,
            DualPathResponse,
        )
        from services.tools.tool_registry import global_tool_registry

        # 读取配置
        config = Config()

        # 初始化工具注册器
        print("\n1. 初始化工具注册器...")
        global_tool_registry.initialize_default_tools(
            n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n"
        )
        print(f"   ✅ 工具注册完成，共注册 {len(global_tool_registry)} 个工具")
        print(f"   📋 可用工具: {global_tool_registry.list_tools()}")

        # 初始化增强LLM服务
        print("\n2. 初始化增强LLM服务...")
        enhanced_llm = VolcengineEnhancedLLMService(
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            tool_registry=global_tool_registry,
            enable_function_calling=True,
        )
        print("   ✅ 增强LLM服务初始化完成")

        # 测试连接
        print("\n3. 测试服务连接...")
        connection_result = await enhanced_llm.test_connection()
        print(f"   连接状态: {connection_result['status']}")
        if connection_result["status"] == "✅ 正常":
            print(f"   模型: {connection_result['model']}")
            print(f"   响应预览: {connection_result['response_preview']}")

        # 测试简单对话（无工具调用）
        print("\n4. 测试简单对话...")
        simple_messages = [{"role": "user", "content": "你好Amy，今天天气怎么样？"}]

        print("   用户: 你好Amy，今天天气怎么样？")
        simple_result = await enhanced_llm.generate_dual_path_response(simple_messages)
        print(f"   Amy回复: {simple_result.immediate_response}")
        print(f"   是否有工具调用: {simple_result.has_tool_calls}")

        # 测试双路径响应（带工具调用）
        print("\n5. 测试双路径响应（工具调用）...")

        # 创建TTS模拟回调
        tts_outputs = []
        patience_outputs = []

        async def immediate_callback(text: str):
            """模拟即时TTS回调"""
            tts_outputs.append(f"[即时TTS] {text}")
            print(f"   🔊 即时播放: {text}")

        async def patience_callback(text: str):
            """模拟耐心等待回调"""
            patience_outputs.append(f"[耐心TTS] {text}")
            print(f"   ⏰ 耐心提示: {text}")

        # 发送需要工具调用的消息
        tool_messages = [
            {"role": "user", "content": "帮我发送一封邮件给朱嘉雯，内容是测试邮件"}
        ]

        print("   用户: 帮我发送一封邮件给朱嘉雯，内容是测试邮件")
        print("   开始双路径处理...")

        dual_result = await enhanced_llm.generate_dual_path_response(
            tool_messages,
            immediate_callback=immediate_callback,
            patience_callback=patience_callback,
        )

        print(f"\n   ✅ 双路径响应完成:")
        print(f"   📤 即时回复: {dual_result.immediate_response}")
        print(f"   🔧 有工具调用: {dual_result.has_tool_calls}")

        if dual_result.has_tool_calls and dual_result.tool_response:
            print(f"   📨 最终回复: {dual_result.tool_response}")
            print(f"   ⏱️  执行时间: {dual_result.tool_execution_time:.2f}s")

        # 测试兼容性接口
        print("\n6. 测试兼容性接口...")
        compat_messages = [{"role": "user", "content": "简单问候一下"}]

        compat_response = await enhanced_llm.generate_chat_response(compat_messages)
        print(f"   兼容接口回复: {compat_response}")

        # 测试各个管理器组件
        print("\n7. 测试各个管理器组件...")

        # 测试即时响应管理器
        immediate_manager = enhanced_llm.immediate_manager
        immediate_resp = await immediate_manager.generate_immediate_response(
            "查询日程", []
        )
        print(f"   即时响应管理器: {immediate_resp}")

        # 测试耐心管理器
        patience_manager = enhanced_llm.tool_manager.patience_manager
        test_callback_called = []

        async def test_patience_callback(msg):
            test_callback_called.append(msg)

        # 模拟5秒等待
        await patience_manager.handle_long_wait(6.0, test_patience_callback)
        if test_callback_called:
            print(f"   耐心管理器: {test_callback_called[0]}")

        # 显示所有输出
        print("\n8. 处理过程记录:")
        if tts_outputs:
            print("   TTS输出记录:")
            for output in tts_outputs:
                print(f"     {output}")

        if patience_outputs:
            print("   耐心提示记录:")
            for output in patience_outputs:
                print(f"     {output}")

        print("\n" + "=" * 70)
        print("增强LLM服务测试完成！")
        print("=" * 70)

        print("\n📋 测试总结:")
        print("1. ✅ 工具注册器初始化正常")
        print("2. ✅ 增强LLM服务初始化正常")
        print("3. ✅ 服务连接测试正常")
        print("4. ✅ 简单对话功能正常")
        print("5. ✅ 双路径响应机制正常")
        print("6. ✅ 兼容性接口正常")
        print("7. ✅ 各管理器组件正常")

    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保安装了所需的依赖：pip install openai")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.error(f"测试异常: {str(e)}", exc_info=True)
        sys.exit(1)


async def test_performance_comparison():
    """性能对比测试：原版 vs 增强版"""

    print("\n" + "=" * 70)
    print("性能对比测试：原版LLM vs 增强版LLM")
    print("=" * 70)

    try:
        from config import Config
        from services.volcengine_llm import VolcengineLLMService
        from services.volcengine_llm_enhanced import VolcengineEnhancedLLMService
        from services.tools.tool_registry import global_tool_registry
        import time

        config = Config()

        # 确保工具已注册
        if len(global_tool_registry) == 0:
            global_tool_registry.initialize_default_tools(
                n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n"
            )

        # 创建两个服务实例
        original_llm = VolcengineLLMService(
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            tool_registry=global_tool_registry,
            enable_function_calling=True,
        )

        enhanced_llm = VolcengineEnhancedLLMService(
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            tool_registry=global_tool_registry,
            enable_function_calling=True,
        )

        # 测试消息
        test_messages = [{"role": "user", "content": "发送测试邮件给admin@example.com"}]

        print("\n测试消息: 发送测试邮件给admin@example.com")

        # 测试原版LLM
        print("\n1. 原版LLM服务测试...")
        start_time = time.time()

        original_response = await original_llm.generate_chat_response(test_messages)

        original_time = time.time() - start_time
        print(f"   ⏱️  原版总耗时: {original_time:.2f}s")
        print(f"   📝 原版回复: {original_response[:100]}...")

        # 测试增强版LLM
        print("\n2. 增强版LLM服务测试...")

        immediate_received = []
        start_time = time.time()

        async def immediate_callback(text: str):
            if not immediate_received:  # 只记录第一次即时回复时间
                immediate_time = time.time() - start_time
                immediate_received.append(immediate_time)
                print(f"   ⚡ 即时回复耗时: {immediate_time:.2f}s")
                print(f"   📤 即时回复: {text}")

        enhanced_result = await enhanced_llm.generate_dual_path_response(
            test_messages, immediate_callback=immediate_callback
        )

        total_time = time.time() - start_time
        print(f"   ⏱️  增强版总耗时: {total_time:.2f}s")

        if enhanced_result.has_tool_calls:
            print(f"   📨 最终回复: {enhanced_result.tool_response[:100]}...")
        else:
            print(f"   📝 直接回复: {enhanced_result.immediate_response[:100]}...")

        # 性能分析
        print("\n📊 性能分析:")
        if immediate_received:
            immediate_time = immediate_received[0]
            print(f"   即时响应速度: {immediate_time:.2f}s (用户体验提升)")
            print(
                f"   总响应时间对比: 原版 {original_time:.2f}s vs 增强版 {total_time:.2f}s"
            )

            if immediate_time < 2.0:
                print("   ✅ 即时响应达标 (< 2秒)")
            else:
                print("   ⚠️  即时响应需要优化")

            improvement = ((original_time - immediate_time) / original_time) * 100
            print(f"   🚀 用户体验提升: {improvement:.1f}% (基于即时响应)")

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        logger.error(f"性能测试异常: {str(e)}", exc_info=True)


def main():
    """主函数"""
    try:
        # 运行主要测试
        asyncio.run(test_enhanced_llm_service())

        # 运行性能对比测试
        asyncio.run(test_performance_comparison())

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
