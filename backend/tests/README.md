# 火山引擎服务测试指南

## 📋 概述

本测试套件用于验证火山引擎服务的各项功能，包括：

- 🎤 **STT (语音识别)**
- 🤖 **LLM (大模型对话)**
- 🔊 **TTS (语音合成)**
- 🔗 **n8n Webhook 调用**

## 🔧 环境准备

### 1. 安装 Python 依赖

```bash
# 安装测试依赖
pip install -r tests/requirements.txt
```

### 2. 配置环境变量

#### 必需的环境变量：

```bash
# 火山引擎认证配置
export VOLCENGINE_ACCESS_KEY="your_access_key_here"
export VOLCENGINE_SECRET_KEY="your_secret_key_here"
export VOLCENGINE_API_KEY="your_api_key_here"
export VOLCENGINE_REGION="cn-beijing"
```

#### 可选的环境变量：

```bash
# 其他配置
export N8N_WEBHOOK_URL="http://localhost:5678/webhook/your-webhook-id"
export DEFAULT_LLM_MODEL="doubao-pro-32k"
export DEFAULT_TTS_VOICE="zh_female_tianmei"
```

### 3. 获取 API 密钥

#### 火山引擎控制台获取密钥：

1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 进入"访问控制" → "访问密钥"
3. 创建或获取 Access Key 和 Secret Key
4. 进入"豆包大模型" → "API 密钥管理"
5. 创建或获取 API Key (用于 LLM 服务)

## 🚀 运行测试

### 方式 1: 使用便捷脚本

#### Windows 用户：

```cmd
run_tests.bat
```

#### Linux/macOS 用户：

```bash
./run_tests.sh
```

### 方式 2: 使用 Python 脚本

```bash
python run_tests.py
```

### 方式 3: 直接使用 pytest

```bash
# 运行所有测试
pytest tests/test_volcengine_service.py -v

# 运行特定测试
pytest tests/test_volcengine_service.py::TestVolcengineService::test_stt_success -v

# 运行异步测试
pytest tests/test_volcengine_service.py -v --asyncio-mode=auto
```

## 📊 测试类型

### 1. 单元测试 (Unit Tests)

- ✅ 不需要真实 API 密钥
- ✅ 使用模拟数据测试所有功能
- ✅ 测试错误处理和边界情况

### 2. 集成测试 (Integration Tests)

- ⚠️ 需要真实 API 密钥
- ⚠️ 会调用真实的火山引擎 API
- ⚠️ 可能产生费用

## 🧪 测试案例

### STT 测试案例：

- ✅ 成功识别场景
- ✅ API 错误处理
- ✅ 网络错误处理
- ✅ 异常响应格式处理

### LLM 测试案例：

- ✅ 正常对话场景
- ✅ 工具调用场景
- ✅ API Key 缺失处理
- ✅ API 错误处理
- ✅ 网络错误处理

### TTS 测试案例：

- ✅ 正常合成场景
- ✅ 音频数据缺失处理
- ✅ API 错误处理
- ✅ 网络错误处理

### 其他测试：

- ✅ 签名生成测试
- ✅ 服务初始化测试
- ✅ 异步上下文管理器测试
- ✅ 不同区域配置测试

## 📈 测试报告

### 成功输出示例：

```
✅ 所有测试依赖已安装
🚀 开始运行火山引擎服务单元测试...
✅ 所有单元测试通过!
🧪 开始运行集成测试...
🤖 测试大模型服务...
✅ LLM服务正常
🔊 测试语音合成服务...
✅ TTS服务正常，音频大小: 1024 bytes
🎤 测试语音识别服务...
✅ STT服务响应正常
✅ 集成测试通过!
🎉 所有测试通过!
```

### 失败输出示例：

```
❌ LLM服务异常: api_error_401
❌ 集成测试失败!
💥 部分测试失败!
```

## 🛠️ 故障排除

### 常见问题：

#### 1. 认证错误 (401 Unauthorized)

```
❌ LLM API error: 401 - Unauthorized
```

**解决方案：**

- 检查 API Key 是否正确
- 确认 API Key 是否有效且未过期
- 验证服务是否已开通

#### 2. 网络连接错误

```
❌ STT service error: Network error
```

**解决方案：**

- 检查网络连接
- 确认防火墙设置
- 验证 API 端点是否可访问

#### 3. 参数错误 (400 Bad Request)

```
❌ STT API error: 400 - Bad Request
```

**解决方案：**

- 检查请求参数格式
- 确认音频数据格式正确
- 验证模型名称是否正确

#### 4. 配额限制 (429 Too Many Requests)

```
❌ LLM API error: 429 - Too Many Requests
```

**解决方案：**

- 等待一段时间后重试
- 检查 API 调用频率限制
- 升级服务套餐

## 🔍 调试模式

### 启用详细日志：

```bash
# 设置日志级别
export LOG_LEVEL=DEBUG

# 运行测试
python run_tests.py
```

### 查看请求详情：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 贡献指南

### 添加新测试：

1. 在 `test_volcengine_service.py` 中添加测试方法
2. 使用 `@pytest.mark.asyncio` 装饰器（如果是异步测试）
3. 添加适当的模拟数据和断言
4. 运行测试确保通过

### 测试命名规范：

- 单元测试：`test_功能_场景`
- 集成测试：`test_功能_integration`
- 错误测试：`test_功能_error_case`

## 📞 技术支持

如果测试过程中遇到问题，请：

1. 查看测试日志输出
2. 检查 API 密钥配置
3. 验证网络连接
4. 查看火山引擎控制台状态

---

**更新时间：** 2024-01-XX  
**版本：** 1.0.0
