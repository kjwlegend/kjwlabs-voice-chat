"""
后端服务启动脚本
"""
import uvicorn
from config import config
from services import initialize_volcengine_service

def main():
    """启动主函数"""
    # 验证配置
    if not config.validate():
        print("配置验证失败，请检查环境变量设置")
        return
    
    # 初始化火山引擎服务
    if config.VOLCENGINE_ACCESS_KEY and config.VOLCENGINE_SECRET_KEY:
        initialize_volcengine_service(
            access_key=config.VOLCENGINE_ACCESS_KEY,
            secret_key=config.VOLCENGINE_SECRET_KEY,
            region=config.VOLCENGINE_REGION
        )
        print("火山引擎服务已初始化")
    else:
        print("警告：火山引擎服务未初始化，某些功能可能不可用")
    
    # 启动服务
    print(f"启动EchoFlow AI Assistant后端服务...")
    print(f"服务地址: http://{config.HOST}:{config.PORT}")
    print(f"API文档: http://{config.HOST}:{config.PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    main() 