/**
 * 对话系统相关类型定义
 */

// 系统状态枚举
export enum ConversationState {
  IDLE = 'idle', // 空闲状态
  LISTENING = 'listening', // 正在聆听
  THINKING = 'thinking', // 正在思考
  SPEAKING = 'speaking', // 正在说话
  ERROR = 'error', // 错误状态
  CONNECTING = 'connecting', // 连接中
  DISCONNECTED = 'disconnected', // 已断开连接
}

// 消息类型
export enum MessageType {
  // 音频相关
  AUDIO_CHUNK = 'audio_chunk',
  AUDIO_START = 'audio_start',
  AUDIO_END = 'audio_end',

  // STT相关
  STT_PARTIAL = 'stt_partial',
  STT_FINAL = 'stt_final',

  // LLM相关
  LLM_THINKING = 'llm_thinking',
  LLM_RESPONSE = 'llm_response',

  // TTS相关
  TTS_START = 'tts_start',
  TTS_CHUNK = 'tts_chunk',
  TTS_END = 'tts_end',

  // 系统控制
  INTERRUPT = 'interrupt',
  STATE_CHANGE = 'state_change',
  ERROR = 'error',
  HEARTBEAT = 'heartbeat',
}

// WebSocket消息结构
export interface WebSocketMessage {
  type: MessageType
  data: any
  timestamp: number
  id?: string
}

// 音频消息数据
export interface AudioMessageData {
  audioData: ArrayBuffer | Blob | string // 支持Base64字符串
  isLast?: boolean
  format?: string
  sampleRate?: number
}

// STT消息数据
export interface STTMessageData {
  text: string
  confidence?: number
  isFinal: boolean
  startTime?: number
  endTime?: number
}

// LLM响应数据
export interface LLMResponseData {
  text: string
  needsToolCall?: boolean
  toolCalls?: ToolCall[]
  conversationId?: string
}

// 工具调用结构
export interface ToolCall {
  id: string
  name: string
  parameters: Record<string, any>
  result?: any
}

// TTS音频数据
export interface TTSMessageData {
  audioData: ArrayBuffer | Blob
  isLast?: boolean
  chunkIndex?: number
  totalChunks?: number
}

// 错误消息数据
export interface ErrorMessageData {
  code: string
  message: string
  details?: any
  retryable?: boolean
}

// 状态变更数据
export interface StateChangeData {
  from: ConversationState
  to: ConversationState
  reason?: string
  timestamp: number
}

// 对话历史记录
export interface ConversationTurn {
  id: string
  userInput: string
  aiResponse: string
  timestamp: number
  duration: number
  toolCalls?: ToolCall[]
  audioUrl?: string
}

// 性能指标
export interface PerformanceMetrics {
  sttLatency: number // STT延迟 (ms)
  llmLatency: number // LLM延迟 (ms)
  ttsLatency: number // TTS延迟 (ms)
  totalLatency: number // 总延迟 (ms)
  audioQuality: number // 音频质量评分
}

// VAD配置
export interface VADConfig {
  positiveSpeechThreshold: number
  negativeSpeechThreshold: number
  preSpeechPadFrames: number
  redemptionFrames: number
  frameSamples: number
  minSpeechFrames: number
}

// 音频设备信息
export interface AudioDevice {
  deviceId: string
  label: string
  kind: 'audioinput' | 'audiooutput'
  groupId: string
}

// 全局配置
export interface AppConfig {
  apiBaseUrl: string
  wsUrl: string
  audioSampleRate: number
  audioChunkSize: number
  maxRecordingTime: number
  vadConfig: VADConfig
}
