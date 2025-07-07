/**
 * 前端配置文件
 * 项目配置信息
 */

import { AppConfig } from '@/types'

export const appConfig: AppConfig = {
  // API配置
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',

  // 音频配置
  audioSampleRate: parseInt(
    process.env.NEXT_PUBLIC_AUDIO_SAMPLE_RATE || '16000'
  ),
  audioChunkSize: parseInt(process.env.NEXT_PUBLIC_AUDIO_CHUNK_SIZE || '1024'),
  maxRecordingTime: parseInt(
    process.env.NEXT_PUBLIC_MAX_RECORDING_TIME || '300000'
  ), // 5分钟

  // VAD配置
  vadConfig: {
    positiveSpeechThreshold: parseFloat(
      process.env.NEXT_PUBLIC_VAD_POSITIVE_THRESHOLD || '0.8'
    ),
    negativeSpeechThreshold: parseFloat(
      process.env.NEXT_PUBLIC_VAD_NEGATIVE_THRESHOLD || '0.65'
    ),
    preSpeechPadFrames: parseInt(
      process.env.NEXT_PUBLIC_VAD_PRE_SPEECH_PAD || '2'
    ),
    redemptionFrames: parseInt(
      process.env.NEXT_PUBLIC_VAD_REDEMPTION_FRAMES || '8'
    ),
    frameSamples: parseInt(process.env.NEXT_PUBLIC_VAD_FRAME_SAMPLES || '1536'),
    minSpeechFrames: parseInt(
      process.env.NEXT_PUBLIC_VAD_MIN_SPEECH_FRAMES || '4'
    ),
  },
}

// 调试配置
export const debugConfig = {
  enableLogs:
    process.env.NEXT_PUBLIC_ENABLE_CONSOLE_LOGS === 'true' ||
    process.env.NODE_ENV === 'development',
  debugMode:
    process.env.NEXT_PUBLIC_DEBUG_MODE === 'true' ||
    process.env.NODE_ENV === 'development',
  showPerformanceMetrics: process.env.NEXT_PUBLIC_SHOW_METRICS === 'true',
}

// 应用元信息
export const appMeta = {
  name: process.env.NEXT_PUBLIC_APP_NAME || 'EchoFlow',
  version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
  description: '实时对话AI助手',
}

// 验证配置
export function validateConfig(): boolean {
  const requiredEnvVars = ['NEXT_PUBLIC_WS_URL', 'NEXT_PUBLIC_API_BASE_URL']

  const missing = requiredEnvVars.filter((varName) => !process.env[varName])

  if (missing.length > 0) {
    console.warn('Missing environment variables (using defaults):', missing)
    // 不返回false，允许使用默认值
  }

  return true
}
