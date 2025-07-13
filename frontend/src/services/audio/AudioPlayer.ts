/**
 * 音频播放器
 * 负责音频播放功能
 */

export interface AudioPlayerOptions {
  volume?: number
  autoplay?: boolean
}

export type PlaybackStateCallback = (isPlaying: boolean) => void

export class AudioPlayer {
  private currentAudio: HTMLAudioElement | null = null
  private playbackStateCallbacks: PlaybackStateCallback[] = []

  private defaultOptions: AudioPlayerOptions = {
    volume: 1.0,
    autoplay: true,
  }

  constructor() {
    console.log('[AudioPlayer] Initialized')
  }

  /**
   * 播放音频
   */
  async playAudio(
    audioData: Blob | ArrayBuffer | string,
    options?: AudioPlayerOptions
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        console.log('[AudioPlayer] Playing audio')

        // 停止当前播放
        this.stopAudio()

        const playerOptions = { ...this.defaultOptions, ...options }
        this.currentAudio = new Audio()

        // 处理不同类型的音频数据
        let audioUrl: string
        if (typeof audioData === 'string') {
          audioUrl = audioData
        } else if (audioData instanceof ArrayBuffer) {
          const blob = new Blob([audioData], { type: 'audio/webm' })
          audioUrl = URL.createObjectURL(blob)
        } else {
          audioUrl = URL.createObjectURL(audioData)
        }

        this.currentAudio.src = audioUrl
        this.currentAudio.volume = playerOptions.volume!
        this.currentAudio.autoplay = playerOptions.autoplay!

        // 设置事件监听器
        this.currentAudio.onloadstart = () => {
          console.log('[AudioPlayer] Audio loading started')
        }

        this.currentAudio.oncanplay = () => {
          console.log('[AudioPlayer] Audio can play')
        }

        this.currentAudio.onplay = () => {
          console.log('[AudioPlayer] Audio playback started')
          this.notifyPlaybackState(true)
        }

        this.currentAudio.onpause = () => {
          console.log('[AudioPlayer] Audio playback paused')
          this.notifyPlaybackState(false)
        }

        this.currentAudio.onended = () => {
          console.log('[AudioPlayer] Audio playback ended')
          this.notifyPlaybackState(false)
          // 清理URL对象
          if (audioUrl.startsWith('blob:')) {
            URL.revokeObjectURL(audioUrl)
          }
          resolve()
        }

        this.currentAudio.onerror = (error) => {
          console.error('[AudioPlayer] Audio playback error:', error)
          this.notifyPlaybackState(false)
          // 清理URL对象
          if (audioUrl.startsWith('blob:')) {
            URL.revokeObjectURL(audioUrl)
          }
          reject(error)
        }

        this.currentAudio.onloadedmetadata = () => {
          console.log(
            `[AudioPlayer] Audio metadata loaded, duration: ${
              this.currentAudio!.duration
            }s`
          )
        }

        // 开始播放
        if (playerOptions.autoplay) {
          this.currentAudio.play().catch(reject)
        }
      } catch (error) {
        console.error('[AudioPlayer] Failed to play audio:', error)
        reject(error)
      }
    })
  }

  /**
   * 停止音频播放
   */
  stopAudio(): void {
    if (this.currentAudio) {
      console.log('[AudioPlayer] Stopping audio playback')
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
      this.currentAudio = null
      this.notifyPlaybackState(false)
    }
  }

  /**
   * 暂停音频播放
   */
  pauseAudio(): void {
    if (this.currentAudio && !this.currentAudio.paused) {
      console.log('[AudioPlayer] Pausing audio playback')
      this.currentAudio.pause()
    }
  }

  /**
   * 恢复音频播放
   */
  resumeAudio(): void {
    if (this.currentAudio && this.currentAudio.paused) {
      console.log('[AudioPlayer] Resuming audio playback')
      this.currentAudio.play()
    }
  }

  /**
   * 设置音量
   */
  setVolume(volume: number): void {
    if (this.currentAudio) {
      this.currentAudio.volume = Math.max(0, Math.min(1, volume))
      console.log(`[AudioPlayer] Volume set to ${this.currentAudio.volume}`)
    }
  }

  /**
   * 获取当前播放状态
   */
  isPlaying(): boolean {
    return this.currentAudio ? !this.currentAudio.paused : false
  }

  /**
   * 获取当前播放时间
   */
  getCurrentTime(): number {
    return this.currentAudio ? this.currentAudio.currentTime : 0
  }

  /**
   * 获取音频总时长
   */
  getDuration(): number {
    return this.currentAudio ? this.currentAudio.duration : 0
  }

  /**
   * 设置播放位置
   */
  setCurrentTime(time: number): void {
    if (this.currentAudio) {
      this.currentAudio.currentTime = time
    }
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    console.log('[AudioPlayer] Cleaning up resources')
    this.stopAudio()
    this.playbackStateCallbacks = []
  }

  // 回调管理
  onPlaybackState(callback: PlaybackStateCallback): void {
    this.playbackStateCallbacks.push(callback)
  }

  offPlaybackState(callback: PlaybackStateCallback): void {
    const index = this.playbackStateCallbacks.indexOf(callback)
    if (index > -1) {
      this.playbackStateCallbacks.splice(index, 1)
    }
  }

  // 私有方法
  private notifyPlaybackState(isPlaying: boolean): void {
    this.playbackStateCallbacks.forEach((callback) => {
      try {
        callback(isPlaying)
      } catch (error) {
        console.error('[AudioPlayer] Playback state callback error:', error)
      }
    })
  }
}
