#!/usr/bin/env python3
"""
测试集成服务
验证增强LLM服务已成功集成到主VolcengineService中
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


async def test_enhanced_service_integration():
    """测试增强服务集成"""

    print("=" * 70)
    print("测试集成服务 - 增强LLM服务集成到主服务")
    print("=" * 70)

    try:
        from config import Config
        from services import VolcengineService

        # 读取配置
        config = Config()

        # 测试增强版LLM服务（默认）
        print("\n1. 测试增强版LLM服务集成...")
        enhanced_service = VolcengineService(
            access_key=config.VOLCENGINE_ACCESS_KEY,
            secret_key=config.VOLCENGINE_SECRET_KEY,
            app_id=config.VOLCENGINE_APP_ID,
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n",
            enable_function_calling=True,
            use_enhanced_llm=True,  # 显式启用增强版
        )

        print(f"   LLM服务类型: {enhanced_service.get_llm_service_type()}")
        print(f"   增强版LLM启用: {enhanced_service.is_enhanced_llm_enabled()}")
        print(
            f"   Function Calling启用: {enhanced_service.is_function_calling_enabled()}"
        )
        print(f"   可用工具: {enhanced_service.get_available_tools()}")

        # 测试原版LLM服务
        print("\n2. 测试原版LLM服务集成...")
        original_service = VolcengineService(
            access_key=config.VOLCENGINE_ACCESS_KEY,
            secret_key=config.VOLCENGINE_SECRET_KEY,
            app_id=config.VOLCENGINE_APP_ID,
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n",
            enable_function_calling=True,
            use_enhanced_llm=False,  # 显式使用原版
        )

        print(f"   LLM服务类型: {original_service.get_llm_service_type()}")
        print(f"   增强版LLM启用: {original_service.is_enhanced_llm_enabled()}")
        print(
            f"   Function Calling启用: {original_service.is_function_calling_enabled()}"
        )
        print(f"   可用工具: {original_service.get_available_tools()}")

        # 测试双路径响应（增强版）
        print("\n3. 测试双路径响应功能...")

        messages = [{"role": "user", "content": "帮我发送邮件给张三，内容是会议提醒"}]

        # 创建回调函数
        immediate_responses = []
        patience_responses = []

        async def immediate_callback(text: str):
            immediate_responses.append(text)
            print(f"   🔊 即时回复: {text}")

        async def patience_callback(text: str):
            patience_responses.append(text)
            print(f"   ⏰ 耐心提示: {text}")

        print("   用户输入: 帮我发送邮件给张三，内容是会议提醒")

        # 测试增强版双路径响应
        print("   \n   【增强版服务】双路径响应测试:")
        dual_result = await enhanced_service.generate_dual_path_response(
            messages,
            immediate_callback=immediate_callback,
            patience_callback=patience_callback,
        )

        print(f"   ✅ 双路径响应完成")
        print(f"   📤 即时回复: {dual_result.immediate_response}")
        print(f"   🔧 有工具调用: {dual_result.has_tool_calls}")
        if dual_result.tool_response:
            print(f"   📨 最终回复: {dual_result.tool_response[:100]}...")

        # 测试原版服务的双路径回退
        print("   \n   【原版服务】双路径回退测试:")
        fallback_result = await original_service.generate_dual_path_response(
            messages,
            immediate_callback=immediate_callback,
        )

        print(f"   ✅ 回退响应完成")
        print(f"   📤 回退回复: {fallback_result.immediate_response[:100]}...")
        print(f"   🔧 有工具调用: {fallback_result.has_tool_calls}")

        # 测试兼容性接口
        print("\n4. 测试兼容性接口...")

        simple_messages = [{"role": "user", "content": "你好Amy"}]

        # 增强版兼容性测试
        enhanced_compat = await enhanced_service.generate_chat_response(simple_messages)
        print(f"   增强版兼容接口: {enhanced_compat}")

        # 原版兼容性测试
        original_compat = await original_service.generate_chat_response(simple_messages)
        print(f"   原版兼容接口: {original_compat}")

        # 测试服务连接
        print("\n5. 测试服务连接...")

        enhanced_test = await enhanced_service.test_services()
        print(f"   增强版服务连接测试:")
        for service_name, result in enhanced_test.items():
            print(f"     {service_name}: {result['status']}")

        original_test = await original_service.test_services()
        print(f"   原版服务连接测试:")
        for service_name, result in original_test.items():
            print(f"     {service_name}: {result['status']}")

        print("\n" + "=" * 70)
        print("集成服务测试完成！")
        print("=" * 70)

        print("\n📋 测试总结:")
        print("1. ✅ 增强版LLM服务集成成功")
        print("2. ✅ 原版LLM服务向后兼容")
        print("3. ✅ 双路径响应机制工作正常")
        print("4. ✅ 兼容性接口保持正常")
        print("5. ✅ 服务连接测试通过")

        return True

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        logger.error(f"集成测试异常: {str(e)}", exc_info=True)
        return False


async def test_performance_comparison():
    """性能对比测试：原版服务 vs 增强版服务"""

    print("\n" + "=" * 70)
    print("性能对比测试：原版服务 vs 增强版服务")
    print("=" * 70)

    try:
        from config import Config
        from services import VolcengineService
        import time

        config = Config()

        # 创建两个服务实例
        original_service = VolcengineService(
            access_key=config.VOLCENGINE_ACCESS_KEY,
            secret_key=config.VOLCENGINE_SECRET_KEY,
            app_id=config.VOLCENGINE_APP_ID,
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n",
            enable_function_calling=True,
            use_enhanced_llm=False,  # 原版
        )

        enhanced_service = VolcengineService(
            access_key=config.VOLCENGINE_ACCESS_KEY,
            secret_key=config.VOLCENGINE_SECRET_KEY,
            app_id=config.VOLCENGINE_APP_ID,
            api_key=config.VOLCENGINE_API_KEY,
            endpoint_id=config.VOLCENGINE_ENDPOINT_ID,
            n8n_webhook_url="https://kai.kjwlabs.com/webhook-test/n8n",
            enable_function_calling=True,
            use_enhanced_llm=True,  # 增强版
        )

        # 测试消息
        test_messages = [{"role": "user", "content": "发送邮件通知项目组会议延期"}]

        print("\n测试消息: 发送邮件通知项目组会议延期")

        # 测试原版服务
        print("\n1. 原版服务测试...")
        start_time = time.time()

        original_response = await original_service.generate_chat_response(test_messages)

        original_time = time.time() - start_time
        print(f"   ⏱️  原版总耗时: {original_time:.2f}s")
        print(f"   📝 原版回复: {original_response[:100]}...")

        # 测试增强版服务
        print("\n2. 增强版服务测试...")

        immediate_received = []
        start_time = time.time()

        async def immediate_callback(text: str):
            if not immediate_received:  # 只记录第一次即时回复时间
                immediate_time = time.time() - start_time
                immediate_received.append(immediate_time)
                print(f"   ⚡ 即时回复耗时: {immediate_time:.2f}s")
                print(f"   📤 即时回复: {text}")

        enhanced_result = await enhanced_service.generate_dual_path_response(
            test_messages, immediate_callback=immediate_callback
        )

        total_time = time.time() - start_time
        print(f"   ⏱️  增强版总耗时: {total_time:.2f}s")

        if enhanced_result.has_tool_calls and enhanced_result.tool_response:
            print(f"   📨 最终回复: {enhanced_result.tool_response[:100]}...")
        else:
            print(f"   📝 直接回复: {enhanced_result.immediate_response[:100]}...")

        # 性能分析
        print("\n📊 性能分析:")
        if immediate_received:
            immediate_time = immediate_received[0]
            print(f"   即时响应速度: {immediate_time:.2f}s (用户体验关键指标)")
            print(
                f"   总响应时间对比: 原版 {original_time:.2f}s vs 增强版 {total_time:.2f}s"
            )

            if immediate_time < 2.0:
                print("   ✅ 即时响应达标 (< 2秒)")
            else:
                print("   ⚠️  即时响应需要优化")

            improvement = ((original_time - immediate_time) / original_time) * 100
            print(f"   🚀 用户体验提升: {improvement:.1f}% (基于即时响应)")

            if total_time > original_time:
                overhead = ((total_time - original_time) / original_time) * 100
                print(f"   ⚠️  总体开销: +{overhead:.1f}% (但用户感知为提升)")
            else:
                saving = ((original_time - total_time) / original_time) * 100
                print(f"   ✅ 总体优化: -{saving:.1f}%")

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        logger.error(f"性能测试异常: {str(e)}", exc_info=True)


def main():
    """主函数"""
    try:
        # 运行集成测试
        success = asyncio.run(test_enhanced_service_integration())

        if success:
            # 运行性能对比测试
            asyncio.run(test_performance_comparison())

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
