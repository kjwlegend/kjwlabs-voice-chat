"""
应用配置文件
管理所有环境变量和应用配置
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类 - 集中管理所有配置项"""

    # 火山引擎API配置
    VOLCENGINE_ACCESS_KEY: str = os.getenv("VOLCENGINE_ACCESS_KEY", "")
    VOLCENGINE_SECRET_KEY: str = os.getenv("VOLCENGINE_SECRET_KEY", "")
    VOLCENGINE_API_KEY: str = os.getenv("VOLCENGINE_API_KEY", "")  # LLM服务
    VOLCENGINE_APP_ID: str = os.getenv("VOLCENGINE_APP_ID", "")  # 语音服务
    VOLCENGINE_ENDPOINT_ID: str = os.getenv("VOLCENGINE_ENDPOINT_ID", "")  # LLM端点
    VOLCENGINE_REGION: str = os.getenv("VOLCENGINE_REGION", "cn-beijing")

    # n8n配置
    N8N_WEBHOOK_URL: str = os.getenv(
        "N8N_WEBHOOK_URL", "http://localhost:5678/webhook/your-webhook-id"
    )

    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # 前端CORS配置
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # 音频配置
    AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    AUDIO_CHUNK_SIZE: int = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))

    # 模型配置
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "doubao-pro-128k")
    DEFAULT_TTS_VOICE: str = os.getenv(
        "DEFAULT_TTS_VOICE", "zh_female_wanwanxiaohe_moon_bigtts"
    )

    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
    WS_MAX_CONNECTION_TIME: int = int(os.getenv("WS_MAX_CONNECTION_TIME", "3600"))

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # 缓存配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_EXPIRE_TIME: int = int(os.getenv("CACHE_EXPIRE_TIME", "3600"))

    # 数据库配置（如果需要）
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./echoflow.db")

    # 开发环境配置
    DEVELOPMENT_MODE: bool = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"
    ENABLE_MOCK_SERVICES: bool = (
        os.getenv("ENABLE_MOCK_SERVICES", "False").lower() == "true"
    )

    @classmethod
    def validate(cls) -> bool:
        """验证配置是否完整"""
        # 基础语音服务需要的变量
        required_vars = [
            "VOLCENGINE_ACCESS_KEY",
            "VOLCENGINE_SECRET_KEY",
            "VOLCENGINE_APP_ID",
        ]

        # LLM服务需要的额外变量
        llm_vars = ["VOLCENGINE_API_KEY", "VOLCENGINE_ENDPOINT_ID"]

        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)

        missing_llm_vars = []
        for var in llm_vars:
            if not getattr(cls, var):
                missing_llm_vars.append(var)

        if missing_vars:
            print(f"❌ 缺少必要的环境变量: {', '.join(missing_vars)}")
            print("请设置以下环境变量：")
            print("VOLCENGINE_ACCESS_KEY=your_access_key_here  # 语音服务认证")
            print("VOLCENGINE_SECRET_KEY=your_secret_key_here  # 密钥")
            print("VOLCENGINE_APP_ID=your_app_id_here         # 语音服务应用ID")
            return False

        if missing_llm_vars:
            print(f"⚠️  LLM服务配置不完整，缺少: {', '.join(missing_llm_vars)}")
            print("LLM服务需要额外配置：")
            print("VOLCENGINE_API_KEY=your_api_key_here       # LLM服务认证")
            print("VOLCENGINE_ENDPOINT_ID=your_endpoint_id    # LLM端点ID")
            print("语音服务仍可正常工作，但大模型对话功能将不可用")

        return True

    @classmethod
    def has_llm_config(cls) -> bool:
        """检查是否有完整的LLM配置"""
        return bool(cls.VOLCENGINE_API_KEY and cls.VOLCENGINE_ENDPOINT_ID)

    @classmethod
    def has_voice_config(cls) -> bool:
        """检查是否有完整的语音服务配置"""
        return bool(
            cls.VOLCENGINE_ACCESS_KEY
            and cls.VOLCENGINE_SECRET_KEY
            and cls.VOLCENGINE_APP_ID
        )

    @classmethod
    def get_cors_origins(cls) -> list:
        """获取CORS允许的源"""
        origins = [cls.FRONTEND_URL]
        if cls.DEBUG:
            # 开发环境添加额外的源
            origins.extend(
                [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:3001",
                    "http://127.0.0.1:3001",
                ]
            )
        return origins

    @classmethod
    def is_production(cls) -> bool:
        """判断是否为生产环境"""
        return not cls.DEVELOPMENT_MODE

    @classmethod
    def print_config(cls) -> None:
        """打印配置信息（安全）"""
        print("=== 🚀 EchoFlow Configuration ===")
        print(f"Environment: {'Production' if cls.is_production() else 'Development'}")
        print(f"Host: {cls.HOST}:{cls.PORT}")
        print(f"Debug: {cls.DEBUG}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Frontend URL: {cls.FRONTEND_URL}")
        print(f"Volcengine Region: {cls.VOLCENGINE_REGION}")
        print("")
        print("🔊 语音服务配置:")
        if cls.VOLCENGINE_ACCESS_KEY:
            print(f"  ✅ Access Key: {cls.VOLCENGINE_ACCESS_KEY[:10]}...")
        else:
            print(f"  ❌ Access Key: 未配置")
        if cls.VOLCENGINE_APP_ID:
            print(f"  ✅ App ID: {cls.VOLCENGINE_APP_ID}")
        else:
            print(f"  ❌ App ID: 未配置")
        print("")
        print("🤖 LLM服务配置:")
        if cls.VOLCENGINE_API_KEY:
            print(f"  ✅ API Key: {cls.VOLCENGINE_API_KEY[:10]}...")
        else:
            print(f"  ❌ API Key: 未配置")
        if cls.VOLCENGINE_ENDPOINT_ID:
            print(f"  ✅ Endpoint ID: {cls.VOLCENGINE_ENDPOINT_ID}")
        else:
            print(f"  ❌ Endpoint ID: 未配置")
        print("")
        print(f"Default TTS Voice: {cls.DEFAULT_TTS_VOICE}")
        print("==============================")


# 创建配置实例
config = Config()
