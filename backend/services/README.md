# 火山引擎服务模块

## 概述

本模块提供了火山引擎语音服务的完整集成，包括：

- 🤖 **LLM 服务**：豆包大语言模型对话
- 🔊 **TTS 服务**：文本转语音合成
- 🎤 **STT 服务**：语音识别转文本 (基于官方 WebSocket 协议)

## 架构设计

### 模块化架构

```
backend/services/
├── __init__.py              # 模块导出
├── volcengine_service.py    # 主服务类 (统一接口)
├── volcengine_llm.py        # LLM服务 (豆包模型)
├── volcengine_tts.py        # TTS服务 (语音合成)
├── volcengine_stt.py        # STT服务 (语音识别 - WebSocket)
└── volce_demo/              # 官方Demo参考
    ├── sauc_websocket_demo.py
    ├── tts_http_demo.py
    └── tts_websocket_demo.py
```

### 主要优化

1. **模块化分离**：从 351 行的单一文件重构为 4 个专门的服务模块
2. **真正的 STT 实现**：基于官方 WebSocket demo，支持完整的二进制协议
3. **流式响应支持**：LLM 服务支持流式和非流式响应
4. **测试模式**：支持测试环境下的模拟响应
5. **错误处理**：完善的异常处理和日志记录

## 使用方式

### 基本初始化

```python
from services import VolcengineService

# 完整初始化
service = VolcengineService(
    access_key="your_access_key",      # 语音服务密钥
    secret_key="your_secret_key",
    app_id="your_app_id",              # 应用ID
    api_key="your_api_key",            # LLM服务密钥
    endpoint_id="your_endpoint_id",    # LLM端点ID
    test_mode=False                    # 生产环境
)

# 测试模式初始化
service = VolcengineService(
    access_key="test_key",
    secret_key="test_secret",
    app_id="test_app",
    test_mode=True  # STT返回模拟结果
)
```

### LLM 服务使用

```python
# 普通对话
messages = [{"role": "user", "content": "你好"}]
response = await service.generate_chat_response(messages)
print(response)  # 豆包的回复

# 流式响应
async for chunk in service.generate_streaming_response(messages):
    print(chunk, end="", flush=True)
```

### TTS 服务使用

```python
# 基本语音合成
audio_data = await service.text_to_speech("这是一个测试")
with open("output.mp3", "wb") as f:
    f.write(audio_data)

# 自定义参数
audio_data = await service.text_to_speech(
    "测试文本",
    voice_type="zh_male_xiaofeng_moon_bigtts",
    speed_ratio=1.2,
    volume_ratio=0.8
)

# 获取可用语音列表
voices = await service.get_available_voices()
```

### STT 服务使用

```python
# 语音识别
with open("audio.wav", "rb") as f:
    audio_data = f.read()

text = await service.speech_to_text(audio_data)
print(f"识别结果: {text}")

# 自定义参数
text = await service.speech_to_text(
    audio_data,
    model_name="bigmodel",
    enable_punc=True,
    enable_itn=True
)
```

## 配置说明

### 环境变量

```env
# 语音服务 (TTS/STT)
VOLCENGINE_ACCESS_KEY=your_access_key
VOLCENGINE_SECRET_KEY=your_secret_key
VOLCENGINE_APP_ID=your_app_id

# LLM服务
VOLCENGINE_API_KEY=your_api_key
VOLCENGINE_ENDPOINT_ID=your_endpoint_id
```

### 服务配置

#### TTS 默认配置

```python
{
    "cluster": "volcano_tts",
    "voice_type": "zh_female_wanwanxiaohe_moon_bigtts",
    "encoding": "mp3",
    "speed_ratio": 1.0,
    "volume_ratio": 1.0,
    "pitch_ratio": 1.0,
    "operation": "query",
    "with_frontend": 1,
    "frontend_type": "unitTson"
}
```

#### STT 默认配置

```python
{
    "model_name": "bigmodel",
    "enable_itn": True,
    "enable_punc": True,
    "enable_ddc": True,
    "show_utterances": True,
    "enable_nonstream": False,
    "audio_format": "wav",
    "codec": "raw",
    "sample_rate": 16000,
    "bits": 16,
    "channel": 1
}
```

## 技术实现

### STT WebSocket 协议

基于官方 demo 实现了完整的二进制协议：

1. **协议头**：4 字节二进制头，包含版本、消息类型等
2. **消息类型**：

   - `CLIENT_FULL_REQUEST`: 初始化请求
   - `CLIENT_AUDIO_ONLY_REQUEST`: 音频数据
   - `SERVER_FULL_RESPONSE`: 服务器响应
   - `SERVER_ERROR_RESPONSE`: 错误响应

3. **数据流程**：
   - 建立 WebSocket 连接
   - 发送初始化请求
   - 分段发送音频数据
   - 接收识别结果
   - 解析和合并文本

### 认证机制

- **语音服务**：使用`access_key`进行 Bearer 认证
- **LLM 服务**：使用`api_key`进行 Bearer 认证

### 错误处理

- 网络错误重试机制
- 详细的错误日志记录
- 优雅的异常处理和错误提示

## 测试

### 单元测试

```bash
# 运行单元测试
python -m pytest tests/test_volcengine_service.py -v

# 运行完整测试套件
python run_tests.py
```

### 测试覆盖

- ✅ 服务初始化测试
- ✅ LLM 服务功能测试
- ✅ TTS 服务功能测试
- ✅ STT 服务功能测试
- ✅ 错误场景测试
- ✅ 集成测试

## 性能优化

1. **异步处理**：全异步架构，支持并发请求
2. **连接复用**：WebSocket 连接自动管理
3. **分段传输**：STT 音频数据分段传输，降低延迟
4. **内存优化**：音频数据流式处理，避免内存溢出

## 日志系统

详细的日志记录：

- 请求/响应状态
- 错误信息和堆栈跟踪
- 性能指标（响应时间、数据大小）
- 调试信息（参数、配置）

## 注意事项

1. **音频格式**：STT 服务推荐使用 16kHz 单声道 WAV 格式
2. **API 限制**：注意各服务的调用频率限制
3. **网络环境**：WebSocket 连接需要稳定的网络环境
4. **密钥安全**：生产环境请妥善保管 API 密钥

## 版本历史

### v2.0.0 (2025-07-12)

- 🎉 完成模块化重构
- ✨ 基于官方 demo 实现真正的 STT 服务
- 🚀 支持流式 LLM 响应
- 🧪 完善的测试覆盖
- 📝 详细的文档和注释

### v1.0.0 (之前)

- 基础的火山引擎服务集成
- 简单的 TTS 和 LLM 功能
- STT 模拟实现
