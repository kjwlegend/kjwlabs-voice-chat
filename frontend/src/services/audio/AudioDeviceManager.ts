/**
 * 音频设备管理器
 * 负责音频设备管理和兼容性检查
 */

import { AudioDevice } from '@/types'

export interface AudioSupport {
  mediaRecorder: boolean
  audioContext: boolean
  getUserMedia: boolean
}

export class AudioDeviceManager {
  constructor() {
    console.log('[AudioDeviceManager] Initialized')
  }

  /**
   * 获取音频设备列表
   */
  async getAudioDevices(): Promise<AudioDevice[]> {
    try {
      console.log('[AudioDeviceManager] Getting audio devices')

      // 首先请求权限以获取设备标签
      await this.requestPermissions()

      const devices = await navigator.mediaDevices.enumerateDevices()
      const audioDevices = devices
        .filter(
          (device) =>
            device.kind === 'audioinput' || device.kind === 'audiooutput'
        )
        .map((device) => ({
          deviceId: device.deviceId,
          label:
            device.label || `${device.kind} - ${device.deviceId.slice(0, 8)}`,
          kind: device.kind as 'audioinput' | 'audiooutput',
          groupId: device.groupId,
        }))

      console.log(
        `[AudioDeviceManager] Found ${audioDevices.length} audio devices`
      )
      return audioDevices
    } catch (error) {
      console.error('[AudioDeviceManager] Failed to get audio devices:', error)
      throw error
    }
  }

  /**
   * 获取默认音频输入设备
   */
  async getDefaultInputDevice(): Promise<AudioDevice | null> {
    try {
      const devices = await this.getAudioDevices()
      const inputDevices = devices.filter(
        (device) => device.kind === 'audioinput'
      )

      // 查找默认设备（通常deviceId为'default'）
      const defaultDevice = inputDevices.find(
        (device) => device.deviceId === 'default'
      )
      if (defaultDevice) {
        return defaultDevice
      }

      // 如果没有标记为default的设备，返回第一个输入设备
      return inputDevices.length > 0 ? inputDevices[0] : null
    } catch (error) {
      console.error(
        '[AudioDeviceManager] Failed to get default input device:',
        error
      )
      return null
    }
  }

  /**
   * 获取默认音频输出设备
   */
  async getDefaultOutputDevice(): Promise<AudioDevice | null> {
    try {
      const devices = await this.getAudioDevices()
      const outputDevices = devices.filter(
        (device) => device.kind === 'audiooutput'
      )

      // 查找默认设备
      const defaultDevice = outputDevices.find(
        (device) => device.deviceId === 'default'
      )
      if (defaultDevice) {
        return defaultDevice
      }

      // 如果没有标记为default的设备，返回第一个输出设备
      return outputDevices.length > 0 ? outputDevices[0] : null
    } catch (error) {
      console.error(
        '[AudioDeviceManager] Failed to get default output device:',
        error
      )
      return null
    }
  }

  /**
   * 测试音频设备
   */
  async testAudioDevice(deviceId: string): Promise<boolean> {
    try {
      console.log(`[AudioDeviceManager] Testing audio device: ${deviceId}`)

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: { exact: deviceId },
        },
      })

      // 测试成功，停止流
      stream.getTracks().forEach((track) => track.stop())

      console.log(
        `[AudioDeviceManager] Audio device test successful: ${deviceId}`
      )
      return true
    } catch (error) {
      console.error(
        `[AudioDeviceManager] Audio device test failed: ${deviceId}`,
        error
      )
      return false
    }
  }

  /**
   * 检查浏览器音频支持
   */
  checkAudioSupport(): AudioSupport {
    const support = {
      mediaRecorder: typeof MediaRecorder !== 'undefined',
      audioContext:
        typeof AudioContext !== 'undefined' ||
        typeof (window as any).webkitAudioContext !== 'undefined',
      getUserMedia: typeof navigator.mediaDevices?.getUserMedia !== 'undefined',
    }

    console.log('[AudioDeviceManager] Audio support check:', support)
    return support
  }

  /**
   * 检查MediaRecorder支持的MIME类型
   */
  getSupportedMimeTypes(): string[] {
    const mimeTypes = [
      'audio/wav',
      'audio/webm;codecs=opus',
      'audio/webm;codecs=pcm',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
      'audio/mpeg',
      'audio/aac',
    ]

    const supportedTypes = mimeTypes.filter((type) => {
      try {
        return MediaRecorder.isTypeSupported(type)
      } catch {
        return false
      }
    })

    console.log('[AudioDeviceManager] Supported MIME types:', supportedTypes)
    return supportedTypes
  }

  /**
   * 获取浏览器音频上下文信息
   */
  getAudioContextInfo(): {
    sampleRate: number
    state: AudioContextState
    baseLatency?: number
    outputLatency?: number
  } | null {
    try {
      const AudioContextClass =
        window.AudioContext || (window as any).webkitAudioContext
      if (!AudioContextClass) {
        return null
      }

      const context = new AudioContextClass()
      const info = {
        sampleRate: context.sampleRate,
        state: context.state,
        baseLatency: context.baseLatency,
        outputLatency: context.outputLatency,
      }

      context.close()

      console.log('[AudioDeviceManager] Audio context info:', info)
      return info
    } catch (error) {
      console.error(
        '[AudioDeviceManager] Failed to get audio context info:',
        error
      )
      return null
    }
  }

  /**
   * 请求音频权限
   */
  async requestPermissions(): Promise<void> {
    try {
      console.log('[AudioDeviceManager] Requesting audio permissions')

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      })

      // 立即停止流，只是为了获取权限
      stream.getTracks().forEach((track) => track.stop())

      console.log('[AudioDeviceManager] Audio permissions granted')
    } catch (error) {
      console.error(
        '[AudioDeviceManager] Failed to request audio permissions:',
        error
      )
      throw error
    }
  }

  /**
   * 监听设备变化
   */
  onDeviceChange(callback: (devices: AudioDevice[]) => void): void {
    const handleDeviceChange = async () => {
      try {
        const devices = await this.getAudioDevices()
        callback(devices)
      } catch (error) {
        console.error(
          '[AudioDeviceManager] Device change callback error:',
          error
        )
      }
    }

    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange)

    // 返回清理函数
    return () => {
      navigator.mediaDevices.removeEventListener(
        'devicechange',
        handleDeviceChange
      )
    }
  }

  /**
   * 获取设备详细信息
   */
  async getDeviceDetails(deviceId: string): Promise<{
    capabilities?: MediaTrackCapabilities
    constraints?: MediaTrackConstraints
    settings?: MediaTrackSettings
  }> {
    try {
      console.log(`[AudioDeviceManager] Getting device details: ${deviceId}`)

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: { exact: deviceId },
        },
      })

      const track = stream.getAudioTracks()[0]
      const details = {
        capabilities: track.getCapabilities?.(),
        constraints: track.getConstraints?.(),
        settings: track.getSettings?.(),
      }

      // 停止流
      stream.getTracks().forEach((track) => track.stop())

      console.log(
        `[AudioDeviceManager] Device details for ${deviceId}:`,
        details
      )
      return details
    } catch (error) {
      console.error(
        `[AudioDeviceManager] Failed to get device details: ${deviceId}`,
        error
      )
      throw error
    }
  }
}
