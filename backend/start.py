"""
后端服务启动脚本
"""

import uvicorn
from config import config
from services import VolcengineService


def main():
    """启动主函数"""
    # 验证基础配置
    if not config.validate():
        print("❌ 配置验证失败，请检查环境变量设置")
        return

    # 初始化火山引擎服务
    global volcengine_service
    volcengine_service = None

    if config.has_voice_config():
        try:
            # 创建火山引擎服务实例
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
            )

            print("🔊 火山引擎语音服务已初始化")

            if config.has_llm_config():
                print("🤖 火山引擎LLM服务已初始化")
            else:
                print("⚠️  LLM服务未配置，大模型对话功能将不可用")

        except Exception as e:
            print(f"❌ 火山引擎服务初始化失败: {e}")
            return
    else:
        print("⚠️  火山引擎语音服务未配置，某些功能可能不可用")
        print(
            "请设置必要的环境变量：VOLCENGINE_ACCESS_KEY, VOLCENGINE_SECRET_KEY, VOLCENGINE_APP_ID"
        )

    # 启动服务
    print("\n🚀 启动EchoFlow AI Assistant后端服务...")
    print(f"📡 服务地址: http://{config.HOST}:{config.PORT}")
    print(f"📚 API文档: http://{config.HOST}:{config.PORT}/docs")
    print(f"🔧 调试模式: {'开启' if config.DEBUG else '关闭'}")
    print("\n" + "=" * 50)

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
