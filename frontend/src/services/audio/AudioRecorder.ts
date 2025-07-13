/**
 * 音频录制器
 * 负责音频录制功能，支持Web Audio API和MediaRecorder两种方式
 */

import { WAVEncoder } from './WAVEncoder'

export interface AudioRecorderOptions {
  sampleRate?: number
  audioBitsPerSecond?: number
  mimeType?: string
  timeslice?: number
  useWebAudioRecording?: boolean
}

export type AudioChunkCallback = (chunk: Blob) => void
export type RecordingStateCallback = (isRecording: boolean) => void

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null
  private mediaStream: MediaStream | null = null
  private audioContext: AudioContext | null = null
  private audioChunks: Blob[] = []

  // Web Audio API录制相关
  private scriptProcessor: ScriptProcessorNode | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private isWebAudioRecording: boolean = false
  private pcmChunks: Float32Array[] = []
  private wavEncoder: WAVEncoder

  // 回调函数
  private audioChunkCallbacks: AudioChunkCallback[] = []
  private recordingStateCallbacks: RecordingStateCallback[] = []

  // 配置
  private options: AudioRecorderOptions = {
    sampleRate: 16000,
    audioBitsPerSecond: 128000, // 提高音频质量
    mimeType: 'audio/webm;codecs=opus', // 优先使用webm格式
    timeslice: 200,
    useWebAudioRecording: false, // 改为使用MediaRecorder
  }

  private supportedMimeTypes: string[] = [
    'audio/webm;codecs=opus',
    'audio/webm;codecs=pcm',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/mp4',
    'audio/wav', // WAV放在最后，因为Chrome不支持原生录制
  ]

  constructor(options?: AudioRecorderOptions) {
    this.options = { ...this.options, ...options }
    this.wavEncoder = new WAVEncoder(
      this.options.sampleRate,
      1, // 单声道
      16 // 16位深度
    )
    console.log('[AudioRecorder] Initialized with options:', this.options)
  }

  /**
   * 初始化录制器
   */
  async initialize(deviceId?: string): Promise<void> {
    try {
      console.log('[AudioRecorder] Initializing...')

      // 请求音频权限
      const constraints: MediaStreamConstraints = {
        audio: deviceId
          ? {
              deviceId: { exact: deviceId },
              sampleRate: this.options.sampleRate,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            }
          : {
              sampleRate: this.options.sampleRate,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
        video: false,
      }

      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints)
      console.log('[AudioRecorder] Media stream obtained')

      // 创建音频上下文
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext ||
          (window as any).webkitAudioContext)()
        console.log('[AudioRecorder] Audio context created')
      }

      if (this.options.useWebAudioRecording) {
        await this.setupWebAudioRecording()
      } else {
        await this.setupMediaRecorderRecording()
      }

      console.log('[AudioRecorder] Initialization complete')
    } catch (error) {
      console.error('[AudioRecorder] Initialization failed:', error)
      throw error
    }
  }

  /**
   * 设置Web Audio API录制
   */
  private async setupWebAudioRecording(): Promise<void> {
    console.log('[AudioRecorder] Setting up Web Audio API recording')

    if (!this.audioContext || !this.mediaStream) {
      throw new Error('Audio context or media stream not available')
    }

    // 确保音频上下文处于运行状态
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }

    // 创建音频源
    this.source = this.audioContext.createMediaStreamSource(this.mediaStream)

    // 创建脚本处理器
    const bufferSize = 4096
    this.scriptProcessor = this.audioContext.createScriptProcessor(
      bufferSize,
      1,
      1
    )

    // 处理音频数据
    this.scriptProcessor.onaudioprocess = (event) => {
      if (!this.isWebAudioRecording) return

      const inputBuffer = event.inputBuffer
      const inputData = inputBuffer.getChannelData(0)

      // 复制数据
      const pcmChunk = new Float32Array(inputData.length)
      pcmChunk.set(inputData)

      // 获取音频统计信息
      const stats = this.wavEncoder.getAudioStats(pcmChunk)

      // 存储PCM数据
      this.pcmChunks.push(pcmChunk)

      // 每10个块打印一次调试信息
      if (this.pcmChunks.length % 10 === 0) {
        console.log(
          `[AudioRecorder] Captured ${
            this.pcmChunks.length
          } chunks, RMS: ${stats.rmsAmplitude.toFixed(4)}, has audio: ${
            stats.hasContent
          }`
        )
      }

      // 定期发送音频块（用于实时传输）
      if (this.pcmChunks.length % 5 === 0) {
        this.sendRealtimeAudioChunk()
      }
    }

    // 连接音频节点
    this.source.connect(this.scriptProcessor)
    this.scriptProcessor.connect(this.audioContext.destination)

    console.log('[AudioRecorder] Web Audio API recording setup complete')
  }

  /**
   * 设置MediaRecorder录制
   */
  private async setupMediaRecorderRecording(): Promise<void> {
    console.log('[AudioRecorder] Setting up MediaRecorder recording')

    if (!this.mediaStream) {
      throw new Error('Media stream not available')
    }

    // 选择支持的MIME类型
    const mimeType = this.getBestSupportedMimeType()

    this.mediaRecorder = new MediaRecorder(this.mediaStream, {
      mimeType: mimeType,
      audioBitsPerSecond: this.options.audioBitsPerSecond,
    })

    this.setupMediaRecorderEvents()
    console.log('[AudioRecorder] MediaRecorder setup complete')
  }

  /**
   * 发送实时音频块
   */
  private sendRealtimeAudioChunk(): void {
    if (this.pcmChunks.length < 5) return

    // 获取最近的5个块
    const recentChunks = this.pcmChunks.slice(-5)
    const totalLength = recentChunks.reduce(
      (sum, chunk) => sum + chunk.length,
      0
    )
    const mergedPCM = new Float32Array(totalLength)

    let offset = 0
    for (const chunk of recentChunks) {
      mergedPCM.set(chunk, offset)
      offset += chunk.length
    }

    // 编码为WAV
    const wavBuffer = this.wavEncoder.encodeWAV(mergedPCM)
    const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' })

    // 发送音频块
    this.notifyAudioChunk(wavBlob)
  }

  /**
   * 开始录制
   */
  async startRecording(): Promise<void> {
    console.log('[AudioRecorder] Starting recording')

    if (this.options.useWebAudioRecording) {
      if (!this.scriptProcessor) {
        throw new Error('Web Audio recording not initialized')
      }

      // 清空之前的数据
      this.pcmChunks = []
      this.isWebAudioRecording = true

      console.log('[AudioRecorder] Web Audio recording started')
    } else {
      if (!this.mediaRecorder) {
        throw new Error('MediaRecorder not initialized')
      }

      if (this.mediaRecorder.state === 'recording') {
        console.warn('[AudioRecorder] Already recording')
        return
      }

      this.audioChunks = []
      this.mediaRecorder.start(this.options.timeslice)
      console.log('[AudioRecorder] MediaRecorder started')
    }

    this.notifyRecordingState(true)
  }

  /**
   * 停止录制
   */
  async stopRecording(): Promise<Blob> {
    console.log('[AudioRecorder] Stopping recording')

    if (this.options.useWebAudioRecording) {
      return this.stopWebAudioRecording()
    } else {
      return this.stopMediaRecorderRecording()
    }
  }

  /**
   * 停止Web Audio录制
   */
  private async stopWebAudioRecording(): Promise<Blob> {
    if (!this.isWebAudioRecording) {
      throw new Error('No active Web Audio recording')
    }

    this.isWebAudioRecording = false

    console.log(
      `[AudioRecorder] Stopping Web Audio recording, collected ${this.pcmChunks.length} chunks`
    )

    // 合并所有PCM数据
    const totalLength = this.pcmChunks.reduce(
      (sum, chunk) => sum + chunk.length,
      0
    )

    let finalBlob: Blob
    if (totalLength > 0) {
      // 合并所有PCM数据
      const mergedPCM = new Float32Array(totalLength)
      let offset = 0

      for (const chunk of this.pcmChunks) {
        mergedPCM.set(chunk, offset)
        offset += chunk.length
      }

      // 获取最终音频统计信息
      const finalStats = this.wavEncoder.getAudioStats(mergedPCM)
      console.log(`[AudioRecorder] Final audio stats:`, finalStats)

      // 编码为WAV
      const wavBuffer = this.wavEncoder.encodeWAV(mergedPCM)
      finalBlob = new Blob([wavBuffer], { type: 'audio/wav' })

      console.log(
        `[AudioRecorder] Recording complete: ${finalBlob.size} bytes, samples: ${totalLength}`
      )
    } else {
      // 创建空的WAV文件
      const emptyWav = this.wavEncoder.encodeWAV(new Float32Array(0))
      finalBlob = new Blob([emptyWav], { type: 'audio/wav' })
      console.log('[AudioRecorder] No audio data recorded, created empty WAV')
    }

    // 清空数据
    this.pcmChunks = []
    this.notifyRecordingState(false)

    return finalBlob
  }

  /**
   * 停止MediaRecorder录制
   */
  private async stopMediaRecorderRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
        reject(new Error('No active MediaRecorder recording'))
        return
      }

      const handleStop = () => {
        this.mediaRecorder!.removeEventListener('stop', handleStop)
        const mimeType = this.mediaRecorder!.mimeType || 'audio/webm'
        const audioBlob = new Blob(this.audioChunks, { type: mimeType })
        console.log(
          `[AudioRecorder] MediaRecorder stopped: ${audioBlob.size} bytes`
        )
        this.notifyRecordingState(false)
        resolve(audioBlob)
      }

      this.mediaRecorder.addEventListener('stop', handleStop)
      this.mediaRecorder.stop()
    })
  }

  /**
   * 获取录制状态
   */
  getRecordingState(): string {
    if (this.options.useWebAudioRecording) {
      return this.isWebAudioRecording ? 'recording' : 'inactive'
    } else {
      return this.mediaRecorder?.state || 'inactive'
    }
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    console.log('[AudioRecorder] Cleaning up resources')

    // 停止录制
    if (this.options.useWebAudioRecording) {
      this.isWebAudioRecording = false
      this.pcmChunks = []

      if (this.scriptProcessor) {
        this.scriptProcessor.disconnect()
        this.scriptProcessor = null
      }

      if (this.source) {
        this.source.disconnect()
        this.source = null
      }
    } else {
      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.stop()
      }
      this.mediaRecorder = null
    }

    // 关闭媒体流
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop())
      this.mediaStream = null
    }

    // 关闭音频上下文
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close()
      this.audioContext = null
    }

    // 清空数据
    this.audioChunks = []
    this.pcmChunks = []

    // 清空回调
    this.audioChunkCallbacks = []
    this.recordingStateCallbacks = []
  }

  // 回调管理
  onAudioChunk(callback: AudioChunkCallback): void {
    this.audioChunkCallbacks.push(callback)
  }

  offAudioChunk(callback: AudioChunkCallback): void {
    const index = this.audioChunkCallbacks.indexOf(callback)
    if (index > -1) {
      this.audioChunkCallbacks.splice(index, 1)
    }
  }

  onRecordingState(callback: RecordingStateCallback): void {
    this.recordingStateCallbacks.push(callback)
  }

  offRecordingState(callback: RecordingStateCallback): void {
    const index = this.recordingStateCallbacks.indexOf(callback)
    if (index > -1) {
      this.recordingStateCallbacks.splice(index, 1)
    }
  }

  // 私有方法
  private getBestSupportedMimeType(): string {
    // 首先检查首选类型
    if (MediaRecorder.isTypeSupported(this.options.mimeType!)) {
      return this.options.mimeType!
    }

    // 检查支持的MIME类型列表
    for (const mimeType of this.supportedMimeTypes) {
      if (MediaRecorder.isTypeSupported(mimeType)) {
        console.log(`[AudioRecorder] Using supported MIME type: ${mimeType}`)
        return mimeType
      }
    }

    console.warn('[AudioRecorder] No supported MIME types found, using default')
    return 'audio/wav'
  }

  private setupMediaRecorderEvents(): void {
    if (!this.mediaRecorder) return

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data)
        this.notifyAudioChunk(event.data)
      }
    }

    this.mediaRecorder.onstart = () => {
      console.log('[AudioRecorder] MediaRecorder started')
    }

    this.mediaRecorder.onstop = () => {
      console.log('[AudioRecorder] MediaRecorder stopped')
    }

    this.mediaRecorder.onerror = (event) => {
      console.error('[AudioRecorder] MediaRecorder error:', event)
    }
  }

  private notifyAudioChunk(chunk: Blob): void {
    this.audioChunkCallbacks.forEach((callback) => {
      try {
        callback(chunk)
      } catch (error) {
        console.error('[AudioRecorder] Audio chunk callback error:', error)
      }
    })
  }

  private notifyRecordingState(isRecording: boolean): void {
    this.recordingStateCallbacks.forEach((callback) => {
      try {
        callback(isRecording)
      } catch (error) {
        console.error('[AudioRecorder] Recording state callback error:', error)
      }
    })
  }
}
