# EchoFlow 前端

实时对话 AI 助手的前端应用，基于 Next.js 和 TypeScript 构建。

## 📁 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js 13+ App Router
│   ├── components/             # React组件
│   │   └── ui/                # shadcn/ui 组件
│   ├── stores/                # Zustand状态管理
│   │   └── conversationStore.ts
│   ├── services/              # 服务层
│   │   ├── websocketService.ts # WebSocket通信
│   │   └── audioService.ts    # 音频处理
│   ├── utils/                 # 工具函数
│   │   ├── audio.ts          # 音频处理工具
│   │   └── format.ts         # 格式化工具
│   ├── hooks/                 # 自定义Hooks
│   │   ├── useConversation.ts # 对话管理
│   │   └── useVAD.ts         # 语音活动检测
│   ├── types/                 # TypeScript类型定义
│   │   └── conversation.ts
│   └── lib/                   # 第三方库配置
├── public/                    # 静态资源
├── components.json            # shadcn/ui配置
├── tailwind.config.js         # Tailwind CSS配置
├── tsconfig.json             # TypeScript配置
└── package.json              # 依赖管理
```

## 🚀 技术栈

- **框架**: Next.js 14 + TypeScript
- **状态管理**: Zustand
- **UI 组件**: shadcn/ui + Tailwind CSS
- **音频处理**: Web Audio API + MediaRecorder
- **语音检测**: @ricky0123/vad-web
- **实时通信**: WebSocket
- **开发工具**: ESLint + Prettier

## 📦 核心功能模块

### 1. 状态管理 (`stores/`)

- **conversationStore.ts**: 全局对话状态管理
  - 对话状态控制
  - 音频数据管理
  - 错误处理
  - 性能指标追踪

### 2. 服务层 (`services/`)

- **websocketService.ts**: WebSocket 通信服务

  - 自动重连机制
  - 消息队列管理
  - 心跳检测
  - 错误恢复

- **audioService.ts**: 音频处理服务
  - 录音控制
  - 音频播放
  - 格式转换
  - 设备管理

### 3. 自定义 Hooks (`hooks/`)

- **useConversation.ts**: 对话管理 Hook

  - 完整对话流程控制
  - 状态同步
  - 事件处理

- **useVAD.ts**: 语音活动检测 Hook
  - 实时语音检测
  - 静音检测
  - 参数调优

### 4. 工具函数 (`utils/`)

- **audio.ts**: 音频处理工具

  - 格式转换
  - 压缩优化
  - 可视化数据

- **format.ts**: 格式化工具
  - 时间格式化
  - 文件大小格式化
  - 状态显示文本

## 🔧 开发指南

### 环境要求

- Node.js 18+
- npm 或 yarn
- 现代浏览器（支持 Web Audio API）

### 安装依赖

```bash
npm install
```

### 环境配置

创建 `.env.local` 文件：

```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEBUG_MODE=true
```

### 开发运行

```bash
npm run dev
```

### 构建部署

```bash
npm run build
npm start
```

## 📝 使用说明

### 基本使用

```tsx
import { useConversation } from "@/hooks";

function ConversationComponent() {
  const {
    state,
    isConnected,
    connect,
    startConversation,
    stopConversation,
    interrupt,
  } = useConversation();

  return (
    <div>
      <button onClick={connect}>连接</button>
      <button onClick={startConversation}>开始对话</button>
      <button onClick={interrupt}>中断</button>
    </div>
  );
}
```

### 状态管理

```tsx
import { useConversationStore } from "@/stores";

function StatusComponent() {
  const { state, currentText, aiResponse } = useConversationStore();

  return (
    <div>
      <p>状态: {state}</p>
      <p>识别文本: {currentText}</p>
      <p>AI回复: {aiResponse}</p>
    </div>
  );
}
```

### VAD 集成

```tsx
import { useVAD } from "@/hooks";

function VADComponent() {
  const { isListening, isSpeaking, start, stop } = useVAD({
    onSpeechStart: () => console.log("开始说话"),
    onSpeechEnd: () => console.log("停止说话"),
  });

  return (
    <div>
      <button onClick={start}>开始检测</button>
      <button onClick={stop}>停止检测</button>
      <p>正在监听: {isListening ? "是" : "否"}</p>
      <p>正在说话: {isSpeaking ? "是" : "否"}</p>
    </div>
  );
}
```

## 🔍 调试和监控

### 控制台日志

开发模式下，所有服务都会输出详细的调试日志：

```
[WebSocketService] Connected successfully
[AudioService] Recording started
[useConversation] State change: idle -> listening
[useVAD] Speech started
```

### 状态检查

使用浏览器开发者工具的 Redux DevTools 扩展查看状态变化。

### 性能监控

```tsx
import { useConversationStore } from "@/stores";

function MetricsComponent() {
  const { metrics } = useConversationStore();

  return (
    <div>
      <p>STT延迟: {metrics?.sttLatency}ms</p>
      <p>LLM延迟: {metrics?.llmLatency}ms</p>
      <p>TTS延迟: {metrics?.ttsLatency}ms</p>
    </div>
  );
}
```

## 🚨 常见问题

### 1. 麦克风权限被拒绝

确保在 HTTPS 环境下运行，或在 localhost 下测试。

### 2. WebSocket 连接失败

检查后端服务是否启动，并确认 WebSocket URL 配置正确。

### 3. 音频播放问题

某些浏览器要求用户交互后才能播放音频，确保在用户点击后开始音频功能。

### 4. VAD 检测不准确

可以通过 `useVAD` 的 `updateConfig` 方法调整 VAD 参数：

```tsx
const { updateConfig } = useVAD();

updateConfig({
  positiveSpeechThreshold: 0.9, // 提高检测阈值
  minSpeechFrames: 6, // 增加最小语音帧数
});
```

## 📚 参考资料

- [Next.js 文档](https://nextjs.org/docs)
- [Zustand 文档](https://zustand-demo.pmnd.rs/)
- [shadcn/ui 文档](https://ui.shadcn.com/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [@ricky0123/vad-web](https://github.com/ricky0123/vad)
