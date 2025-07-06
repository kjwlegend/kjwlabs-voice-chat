# EchoFlow - 实时对话 AI 助手

## 项目概述

EchoFlow 是一个基于火山引擎服务的高性能、低成本、可打断的对话式 AI 原型。该项目旨在验证通过组合火山引擎的原子服务（STT、LLM、TTS），构建一个功能对齐、成本显著降低的对话 AI 助手。

## 技术架构

- **前端**: Next.js + React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **后端**: Python 3.10+ + FastAPI + WebSocket
- **语音识别**: 火山引擎流式语音识别
- **语言模型**: 火山引擎豆包大模型 (Pro/Skylark)
- **语音合成**: 火山引擎豆包 TTS (流式)
- **语音活动检测**: @ricky0123/vad-web
- **工具执行**: n8n (Webhook)
- **实时通信**: WebSocket

## 项目结构

```
kjwlabs/
├── frontend/                 # Next.js前端项目
│   ├── src/
│   │   ├── app/             # Next.js应用目录
│   │   ├── components/      # React组件
│   │   └── lib/             # 工具函数
│   ├── components.json      # shadcn配置
│   ├── package.json         # 前端依赖
│   └── ...
├── backend/                  # FastAPI后端项目
│   ├── services/            # 服务模块
│   │   ├── __init__.py
│   │   └── volcengine_service.py  # 火山引擎服务集成
│   ├── main.py              # 主应用文件
│   ├── config.py            # 配置文件
│   ├── start.py             # 启动脚本
│   ├── requirements.txt     # Python依赖
│   └── venv/                # 虚拟环境
├── task/                     # 任务管理
│   └── tasks.json           # 详细任务拆解
├── prd.md                   # 产品需求文档
└── README.md               # 项目说明
```

## 核心功能

### 1. 实时对话交互

- 流式语音识别（STT）
- 流式语音合成（TTS）
- 低延迟对话体验（<1.5 秒）

### 2. 语音活动检测

- 自动检测用户说话结束
- 支持语音打断（Barge-in）
- 智能语音活动识别

### 3. 工具调用

- 集成 n8n 作为外部工具执行器
- 支持天气查询、地点推荐等功能
- 灵活的工具扩展机制

### 4. 成本优化

- 相比 ElevenLabs 等方案成本降低 99%+
- 智能资源管理和 API 调用优化
- 可打断的 TTS 节省不必要开销

## 快速开始

### 环境要求

- Node.js 18+
- Python 3.10+
- 火山引擎账户和 API 密钥

### 1. 克隆项目

```bash
git clone <repository-url>
cd kjwlabs
```

### 2. 前端设置

```bash
cd frontend
npm install
npm run dev
```

### 3. 后端设置

```bash
cd backend
source venv/Scripts/activate  # Windows
# 或 source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 设置火山引擎API密钥
export VOLCENGINE_ACCESS_KEY=your_access_key_here
export VOLCENGINE_SECRET_KEY=your_secret_key_here
export VOLCENGINE_REGION=cn-north-1
```

### 5. 启动后端服务

```bash
python start.py
```

## 开发里程碑

### 里程碑 1 - 核心管道搭建 (V0.1)

- [x] 项目初始化与环境搭建
- [ ] 火山引擎 API 集成
- [ ] 基础前端界面开发
- [ ] 基础后端 API 开发
- [ ] 基础功能集成测试

### 里程碑 2 - 实现流式与 VAD (V0.5)

- [ ] WebSocket 通信架构
- [ ] 音频流处理实现
- [ ] 语音活动检测(VAD)集成
- [ ] 流式对话体验优化
- [ ] 流式功能集成测试

### 里程碑 3 - 实现工具调用与打断 (V1.0)

- [ ] n8n 工具调用集成
- [ ] LLM 函数调用实现
- [ ] 语音打断(Barge-in)实现
- [ ] 成本控制优化
- [ ] 错误处理与容错
- [ ] 性能测试与优化
- [ ] 最终集成测试
- [ ] 文档编写与部署

## 性能目标

- **延迟**: 从用户说话结束到 AI 开始响应 < 1.5 秒
- **首字延迟**: AI 开始说话后第一个音频包到达 < 300 毫秒
- **成本**: 相比 ElevenLabs 等方案成本降低 99%+
- **可用性**: 99.9%服务可用率

## 技术特点

1. **模块化架构**: 前后端分离，服务解耦
2. **流式处理**: 实现边听边处理，边生成边播放
3. **智能打断**: 支持自然的语音打断体验
4. **成本优化**: 智能资源管理，最大化成本效益
5. **容错设计**: 完善的错误处理和恢复机制

## 注意事项

1. **volcengine-python-sdk 安装问题**: 由于 Windows 路径长度限制，可能需要手动安装
2. **API 密钥配置**: 需要有效的火山引擎 API 密钥才能正常使用
3. **网络延迟**: 建议在同一地理区域部署以减少网络延迟
4. **音频格式**: 支持常见的音频格式，建议使用 16kHz 采样率

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或联系项目维护者。
