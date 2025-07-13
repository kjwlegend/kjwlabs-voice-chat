/**
 * 音频服务模块导出
 * 导出所有音频相关的类和类型
 */

import { AudioService } from './AudioService'

// 主要服务
export { AudioService } from './AudioService'
export type { AudioServiceOptions } from './AudioService'

// 录制器
export { AudioRecorder } from './AudioRecorder'
export type {
  AudioRecorderOptions,
  AudioChunkCallback,
  RecordingStateCallback,
} from './AudioRecorder'

// 播放器
export { AudioPlayer } from './AudioPlayer'
export type { AudioPlayerOptions, PlaybackStateCallback } from './AudioPlayer'

// 设备管理器
export { AudioDeviceManager } from './AudioDeviceManager'
export type { AudioSupport } from './AudioDeviceManager'

// WAV编码器
export { WAVEncoder } from './WAVEncoder'

// 便利导出：默认导出 AudioService
export default AudioService
