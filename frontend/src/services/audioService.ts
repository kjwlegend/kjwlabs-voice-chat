/**
 * 音频处理服务
 * 管理音频录制、播放和VAD功能
 *
 * 重构后使用模块化架构，将功能分离到不同的类中
 */

import { AudioDevice, VADConfig } from '@/types'
import { AudioService as RefactoredAudioService } from './audio'

// 导出类型以保持向后兼容
export interface AudioRecorderOptions {
  sampleRate?: number
  audioBitsPerSecond?: number
  mimeType?: string
  timeslice?: number
  useWebAudioRecording?: boolean
}

export interface AudioPlayerOptions {
  volume?: number
  autoplay?: boolean
}

export type AudioChunkCallback = (chunk: Blob) => void
export type RecordingStateCallback = (isRecording: boolean) => void
export type PlaybackStateCallback = (isPlaying: boolean) => void

/**
 * AudioService 类
 * 现在使用重构后的模块化架构
 */
export class AudioService {
  private refactoredService: RefactoredAudioService

  constructor() {
    console.log(
      '[AudioService] Initialized with refactored architecture - using webm format'
    )
    this.refactoredService = new RefactoredAudioService({
      recorder: {
        sampleRate: 16000,
        audioBitsPerSecond: 128000,
        mimeType: 'audio/webm;codecs=opus',
        timeslice: 200,
        useWebAudioRecording: false, // 使用MediaRecorder录制webm
      },
      player: {
        volume: 1.0,
        autoplay: true,
      },
    })
  }

  /**
   * 获取音频设备列表
   */
  async getAudioDevices(): Promise<AudioDevice[]> {
    return this.refactoredService.getAudioDevices()
  }

  /**
   * 检查浏览器音频支持
   */
  checkAudioSupport(): {
    mediaRecorder: boolean
    audioContext: boolean
    getUserMedia: boolean
  } {
    return this.refactoredService.checkAudioSupport()
  }

  /**
   * 请求麦克风权限并初始化录制
   */
  async initializeRecording(
    deviceId?: string,
    options?: AudioRecorderOptions
  ): Promise<void> {
    return this.refactoredService.initializeRecording(deviceId)
  }

  /**
   * 开始录制
   */
  startRecording(): void {
    this.refactoredService.startRecording()
  }

  /**
   * 停止录制
   */
  stopRecording(): Promise<Blob> {
    return this.refactoredService.stopRecording()
  }

  /**
   * 暂停录制
   */
  pauseRecording(): void {
    // 目前重构后的服务不支持暂停，可以后续添加
    console.log(
      '[AudioService] Pause recording not implemented in refactored service'
    )
  }

  /**
   * 恢复录制
   */
  resumeRecording(): void {
    // 目前重构后的服务不支持恢复，可以后续添加
    console.log(
      '[AudioService] Resume recording not implemented in refactored service'
    )
  }

  /**
   * 播放音频
   */
  async playAudio(
    audioData: Blob | ArrayBuffer | string,
    options?: AudioPlayerOptions
  ): Promise<void> {
    return this.refactoredService.playAudio(audioData, options)
  }

  /**
   * 停止音频播放
   */
  stopAudio(): void {
    this.refactoredService.stopAudio()
  }

  /**
   * 获取当前录制状态
   */
  getRecordingState(): string {
    return this.refactoredService.getRecordingState()
  }

  /**
   * 获取当前播放状态
   */
  isPlaying(): boolean {
    return this.refactoredService.isPlaying()
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    this.refactoredService.cleanup()
  }

  // 回调管理
  onAudioChunk(callback: AudioChunkCallback): void {
    this.refactoredService.onAudioChunk(callback)
  }

  offAudioChunk(callback: AudioChunkCallback): void {
    this.refactoredService.offAudioChunk(callback)
  }

  onRecordingState(callback: RecordingStateCallback): void {
    this.refactoredService.onRecordingState(callback)
  }

  offRecordingState(callback: RecordingStateCallback): void {
    this.refactoredService.offRecordingState(callback)
  }

  onPlaybackState(callback: PlaybackStateCallback): void {
    this.refactoredService.onPlaybackState(callback)
  }

  offPlaybackState(callback: PlaybackStateCallback): void {
    this.refactoredService.offPlaybackState(callback)
  }

  // 新增的便利方法
  async recordAndPlay(duration: number = 5000): Promise<void> {
    return this.refactoredService.recordAndPlay(duration)
  }

  async getSystemInfo(): Promise<{
    devices: AudioDevice[]
    support: any
    supportedMimeTypes: string[]
    audioContextInfo: any
  }> {
    return this.refactoredService.getSystemInfo()
  }

  // 音频设备管理
  async getDefaultInputDevice(): Promise<AudioDevice | null> {
    return this.refactoredService.getDefaultInputDevice()
  }

  async getDefaultOutputDevice(): Promise<AudioDevice | null> {
    return this.refactoredService.getDefaultOutputDevice()
  }

  async testAudioDevice(deviceId: string): Promise<boolean> {
    return this.refactoredService.testAudioDevice(deviceId)
  }

  getSupportedMimeTypes(): string[] {
    return this.refactoredService.getSupportedMimeTypes()
  }

  getAudioContextInfo() {
    return this.refactoredService.getAudioContextInfo()
  }

  async requestPermissions(): Promise<void> {
    return this.refactoredService.requestPermissions()
  }

  onDeviceChange(callback: (devices: AudioDevice[]) => void): void {
    return this.refactoredService.onDeviceChange(callback)
  }

  async getDeviceDetails(deviceId: string) {
    return this.refactoredService.getDeviceDetails(deviceId)
  }

  // 音频播放器功能
  pauseAudio(): void {
    this.refactoredService.pauseAudio()
  }

  resumeAudio(): void {
    this.refactoredService.resumeAudio()
  }

  setVolume(volume: number): void {
    this.refactoredService.setVolume(volume)
  }

  getCurrentTime(): number {
    return this.refactoredService.getCurrentTime()
  }

  getDuration(): number {
    return this.refactoredService.getDuration()
  }

  setCurrentTime(time: number): void {
    this.refactoredService.setCurrentTime(time)
  }

  // WAV编码功能
  encodeWAV(pcmData: Float32Array): ArrayBuffer {
    return this.refactoredService.encodeWAV(pcmData)
  }

  hasAudioContent(pcmData: Float32Array, threshold?: number): boolean {
    return this.refactoredService.hasAudioContent(pcmData, threshold)
  }

  getAudioStats(pcmData: Float32Array) {
    return this.refactoredService.getAudioStats(pcmData)
  }
}
