"""
FastAPI主应用程序
实时对话AI助手后端服务
"""
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="EchoFlow AI Assistant",
    description="实时对话AI助手后端服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储WebSocket连接
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"客户端 {client_id} 已连接")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"客户端 {client_id} 已断开连接")
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(json.dumps(message))

# 连接管理器实例
manager = ConnectionManager()

@app.get("/")
async def root():
    """根路径健康检查"""
    return {"message": "EchoFlow AI Assistant Backend is running"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "EchoFlow AI Assistant"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接处理"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(f"收到客户端 {client_id} 消息: {message}")
            
            # 处理不同类型的消息
            await handle_message(client_id, message)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(client_id)

async def handle_message(client_id: str, message: dict):
    """处理WebSocket消息"""
    message_type = message.get("type")
    
    if message_type == "audio_chunk":
        # 处理音频流数据
        await process_audio_chunk(client_id, message.get("data"))
    elif message_type == "interrupt":
        # 处理语音打断
        await process_interrupt(client_id)
    elif message_type == "start_conversation":
        # 开始对话
        await start_conversation(client_id)
    elif message_type == "end_conversation":
        # 结束对话
        await end_conversation(client_id)
    else:
        logger.warning(f"未知消息类型: {message_type}")

async def process_audio_chunk(client_id: str, audio_data: str):
    """处理音频流数据"""
    # TODO: 集成火山引擎STT服务
    # 这里将实现：
    # 1. 接收音频流数据
    # 2. 调用火山引擎流式语音识别服务
    # 3. 返回识别结果
    
    await manager.send_message(client_id, {
        "type": "transcription",
        "data": "音频识别结果占位符"
    })

async def process_interrupt(client_id: str):
    """处理语音打断"""
    # TODO: 停止当前TTS播放
    # 这里将实现：
    # 1. 停止当前的TTS生成
    # 2. 清理音频队列
    # 3. 准备接收新的语音输入
    
    await manager.send_message(client_id, {
        "type": "interrupt_acknowledged",
        "data": "打断已处理"
    })

async def start_conversation(client_id: str):
    """开始对话"""
    await manager.send_message(client_id, {
        "type": "conversation_started",
        "data": "对话已开始"
    })

async def end_conversation(client_id: str):
    """结束对话"""
    await manager.send_message(client_id, {
        "type": "conversation_ended",
        "data": "对话已结束"
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 