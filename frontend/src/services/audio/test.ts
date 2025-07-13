/**
 * 重构后的音频服务测试
 * 用于验证所有模块是否正确连接
 */

import { AudioService } from './AudioService'
import { AudioRecorder } from './AudioRecorder'
import { AudioPlayer } from './AudioPlayer'
import { AudioDeviceManager } from './AudioDeviceManager'
import { WAVEncoder } from './WAVEncoder'

// 测试音频服务
export async function testAudioService() {
  console.log('Testing refactored audio service...')

  try {
    // 1. 测试主要服务
    const audioService = new AudioService()
    console.log('✓ AudioService created successfully')

    // 2. 测试设备管理
    const support = audioService.checkAudioSupport()
    console.log('✓ Audio support check:', support)

    const mimeTypes = audioService.getSupportedMimeTypes()
    console.log('✓ Supported MIME types:', mimeTypes)

    // 3. 测试权限请求
    await audioService.requestPermissions()
    console.log('✓ Audio permissions requested')

    // 4. 测试设备列表
    const devices = await audioService.getAudioDevices()
    console.log('✓ Audio devices:', devices.length)

    // 5. 测试初始化录制
    await audioService.initializeRecording()
    console.log('✓ Recording initialized')

    // 6. 测试录制状态
    const recordingState = audioService.getRecordingState()
    console.log('✓ Recording state:', recordingState)

    // 7. 测试系统信息
    const systemInfo = await audioService.getSystemInfo()
    console.log('✓ System info:', systemInfo)

    // 8. 清理资源
    audioService.cleanup()
    console.log('✓ Resources cleaned up')

    console.log('All tests passed! 🎉')
  } catch (error) {
    console.error('Test failed:', error)
    throw error
  }
}

// 测试独立模块
export async function testIndividualModules() {
  console.log('Testing individual modules...')

  try {
    // 1. 测试WAV编码器
    const wavEncoder = new WAVEncoder()
    const testPCM = new Float32Array([0.1, 0.2, 0.3, 0.4, 0.5])
    const wavBuffer = wavEncoder.encodeWAV(testPCM)
    const hasContent = wavEncoder.hasAudioContent(testPCM)
    const stats = wavEncoder.getAudioStats(testPCM)
    console.log('✓ WAV encoder works:', {
      bufferSize: wavBuffer.byteLength,
      hasContent,
      stats,
    })

    // 2. 测试设备管理器
    const deviceManager = new AudioDeviceManager()
    const audioSupport = deviceManager.checkAudioSupport()
    console.log('✓ Device manager works:', audioSupport)

    // 3. 测试音频播放器
    const audioPlayer = new AudioPlayer()
    const isPlaying = audioPlayer.isPlaying()
    console.log('✓ Audio player works:', { isPlaying })
    audioPlayer.cleanup()

    // 4. 测试音频录制器
    const audioRecorder = new AudioRecorder()
    const state = audioRecorder.getRecordingState()
    console.log('✓ Audio recorder works:', { state })
    audioRecorder.cleanup()

    console.log('All module tests passed! 🎉')
  } catch (error) {
    console.error('Module test failed:', error)
    throw error
  }
}

// 导出测试函数
export default {
  testAudioService,
  testIndividualModules,
}
