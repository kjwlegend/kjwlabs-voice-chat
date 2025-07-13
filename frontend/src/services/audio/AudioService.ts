/**
 * 音频服务协调器
 * 协调音频录制、播放和设备管理功能
 */

import {
  AudioRecorder,
  AudioRecorderOptions,
  AudioChunkCallback,
  RecordingStateCallback,
} from './AudioRecorder'
import {
  AudioPlayer,
  AudioPlayerOptions,
  PlaybackStateCallback,
} from './AudioPlayer'
import { AudioDeviceManager, AudioSupport } from './AudioDeviceManager'
import { WAVEncoder } from './WAVEncoder'
import { AudioDevice } from '@/types'

export interface AudioServiceOptions {
  recorder?: AudioRecorderOptions
  player?: AudioPlayerOptions
}

export class AudioService {
  private recorder: AudioRecorder
  private player: AudioPlayer
  private deviceManager: AudioDeviceManager
  private wavEncoder: WAVEncoder

  constructor(options?: AudioServiceOptions) {
    console.log('[AudioService] Initializing with options:', options)

    // 默认使用webm格式录制
    const defaultRecorderOptions = {
      sampleRate: 16000,
      audioBitsPerSecond: 128000,
      mimeType: 'audio/webm;codecs=opus',
      timeslice: 200,
      useWebAudioRecording: false, // 使用MediaRecorder
      ...options?.recorder,
    }

    this.recorder = new AudioRecorder(defaultRecorderOptions)
    this.player = new AudioPlayer()
    this.deviceManager = new AudioDeviceManager()
    this.wavEncoder = new WAVEncoder()

    console.log('[AudioService] Initialized successfully')
  }

  // 录制功能
  async initializeRecording(deviceId?: string): Promise<void> {
    return this.recorder.initialize(deviceId)
  }

  async startRecording(): Promise<void> {
    return this.recorder.startRecording()
  }

  async stopRecording(): Promise<Blob> {
    return this.recorder.stopRecording()
  }

  getRecordingState(): string {
    return this.recorder.getRecordingState()
  }

  onAudioChunk(callback: AudioChunkCallback): void {
    this.recorder.onAudioChunk(callback)
  }

  offAudioChunk(callback: AudioChunkCallback): void {
    this.recorder.offAudioChunk(callback)
  }

  onRecordingState(callback: RecordingStateCallback): void {
    this.recorder.onRecordingState(callback)
  }

  offRecordingState(callback: RecordingStateCallback): void {
    this.recorder.offRecordingState(callback)
  }

  // 播放功能
  async playAudio(
    audioData: Blob | ArrayBuffer | string,
    options?: AudioPlayerOptions
  ): Promise<void> {
    return this.player.playAudio(audioData, options)
  }

  stopAudio(): void {
    this.player.stopAudio()
  }

  pauseAudio(): void {
    this.player.pauseAudio()
  }

  resumeAudio(): void {
    this.player.resumeAudio()
  }

  setVolume(volume: number): void {
    this.player.setVolume(volume)
  }

  isPlaying(): boolean {
    return this.player.isPlaying()
  }

  getCurrentTime(): number {
    return this.player.getCurrentTime()
  }

  getDuration(): number {
    return this.player.getDuration()
  }

  setCurrentTime(time: number): void {
    this.player.setCurrentTime(time)
  }

  onPlaybackState(callback: PlaybackStateCallback): void {
    this.player.onPlaybackState(callback)
  }

  offPlaybackState(callback: PlaybackStateCallback): void {
    this.player.offPlaybackState(callback)
  }

  // 设备管理功能
  async getAudioDevices(): Promise<AudioDevice[]> {
    return this.deviceManager.getAudioDevices()
  }

  async getDefaultInputDevice(): Promise<AudioDevice | null> {
    return this.deviceManager.getDefaultInputDevice()
  }

  async getDefaultOutputDevice(): Promise<AudioDevice | null> {
    return this.deviceManager.getDefaultOutputDevice()
  }

  async testAudioDevice(deviceId: string): Promise<boolean> {
    return this.deviceManager.testAudioDevice(deviceId)
  }

  checkAudioSupport(): AudioSupport {
    return this.deviceManager.checkAudioSupport()
  }

  getSupportedMimeTypes(): string[] {
    return this.deviceManager.getSupportedMimeTypes()
  }

  getAudioContextInfo() {
    return this.deviceManager.getAudioContextInfo()
  }

  async requestPermissions(): Promise<void> {
    return this.deviceManager.requestPermissions()
  }

  onDeviceChange(callback: (devices: AudioDevice[]) => void): void {
    return this.deviceManager.onDeviceChange(callback)
  }

  async getDeviceDetails(deviceId: string) {
    return this.deviceManager.getDeviceDetails(deviceId)
  }

  // WAV编码功能
  encodeWAV(pcmData: Float32Array): ArrayBuffer {
    return this.wavEncoder.encodeWAV(pcmData)
  }

  hasAudioContent(pcmData: Float32Array, threshold?: number): boolean {
    return this.wavEncoder.hasAudioContent(pcmData, threshold)
  }

  getAudioStats(pcmData: Float32Array) {
    return this.wavEncoder.getAudioStats(pcmData)
  }

  // 便利方法
  async recordAndPlay(duration: number = 5000): Promise<void> {
    console.log(`[AudioService] Recording and playing for ${duration}ms`)

    try {
      // 开始录制
      await this.startRecording()

      // 等待指定时间
      await new Promise((resolve) => setTimeout(resolve, duration))

      // 停止录制
      const audioBlob = await this.stopRecording()

      // 播放录制的音频
      await this.playAudio(audioBlob)

      console.log('[AudioService] Record and play completed')
    } catch (error) {
      console.error('[AudioService] Record and play failed:', error)
      throw error
    }
  }

  async getSystemInfo(): Promise<{
    devices: AudioDevice[]
    support: AudioSupport
    supportedMimeTypes: string[]
    audioContextInfo: any
  }> {
    try {
      const [devices, support, supportedMimeTypes, audioContextInfo] =
        await Promise.all([
          this.getAudioDevices(),
          Promise.resolve(this.checkAudioSupport()),
          Promise.resolve(this.getSupportedMimeTypes()),
          Promise.resolve(this.getAudioContextInfo()),
        ])

      return {
        devices,
        support,
        supportedMimeTypes,
        audioContextInfo,
      }
    } catch (error) {
      console.error('[AudioService] Failed to get system info:', error)
      throw error
    }
  }

  // 清理资源
  cleanup(): void {
    console.log('[AudioService] Cleaning up all resources')

    this.recorder.cleanup()
    this.player.cleanup()

    console.log('[AudioService] Cleanup completed')
  }
}
