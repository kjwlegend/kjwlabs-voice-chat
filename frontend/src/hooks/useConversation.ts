/**
 * 对话Hook
 * 管理语音对话的完整流程
 */

import { useCallback, useEffect, useRef } from 'react'
import { useConversationStore } from '@/stores/conversationStore'
import { websocketService } from '@/services/websocketService'
import { audioService } from '@/services'
import { ConversationState, MessageType } from '@/types'

export interface UseConversationReturn {
  // 状态
  state: ConversationState
  isConnected: boolean
  isRecording: boolean
  isPlaying: boolean
  currentText: string
  finalText: string
  aiResponse: string
  error: any

  // 控制方法
  connect: () => Promise<void>
  disconnect: () => void
  startConversation: () => Promise<void>
  stopConversation: () => void
  interrupt: () => void

  // 状态查询
  canStartConversation: boolean
  canInterrupt: boolean
}

export function useConversation(): UseConversationReturn {
  const {
    state,
    isConnected,
    isRecording,
    isPlaying,
    currentText,
    finalText,
    aiResponse,
    error,
    setConnected,
    setRecording,
    setPlaying,
    setError,
    setCurrentAudioUrl,
    handleConnectionEstablished,
    handleSTTStart,
    handleSTTResult,
    handleLLMStart,
    handleLLMResponse,
    handleTTSStart,
    handleTTSResult,
    handleTTSUnavailable,
    handleHeartbeatAck,
    handleError,
    triggerInterrupt,
  } = useConversationStore()

  const isInitialized = useRef(false)
  const audioChunkTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // 连接WebSocket
  const connect = useCallback(async () => {
    try {
      console.log('[useConversation] Connecting to WebSocket...')
      await websocketService.connect()
      console.log('[useConversation] WebSocket connected successfully')
    } catch (error) {
      console.error('[useConversation] Failed to connect:', error)
      setError({
        code: 'CONNECTION_FAILED',
        message: '连接失败，请检查网络',
        retryable: true,
      })
      throw error
    }
  }, [setError])

  // 断开连接
  const disconnect = useCallback(() => {
    console.log('[useConversation] Disconnecting...')
    websocketService.disconnect()
    audioService.cleanup()
  }, [])

  // 开始对话
  const startConversation = useCallback(async () => {
    try {
      console.log('[useConversation] Starting conversation...')
      await audioService.startRecording()
      websocketService.startConversation()
      setRecording(true)
    } catch (error) {
      console.error('[useConversation] Failed to start conversation:', error)
      setError({
        code: 'RECORDING_FAILED',
        message: '录音失败，请检查麦克风权限',
        retryable: true,
      })
      throw error
    }
  }, [setRecording, setError])

  // 停止对话
  const stopConversation = useCallback(() => {
    console.log('[useConversation] Stopping conversation...')
    audioService.stopRecording()
    websocketService.endConversation()
    setRecording(false)
  }, [setRecording])

  // 中断AI说话
  const interrupt = useCallback(() => {
    console.log('[useConversation] Interrupting AI...')

    // 1. 发送中断信号到后端
    websocketService.sendInterrupt()

    // 2. 停止本地音频播放
    audioService.stopAudio()
    setPlaying(false)

    // 3. 更新状态
    triggerInterrupt()

    // 4. 重新开始录制
    try {
      audioService.startRecording()
      setRecording(true)
    } catch (error: any) {
      console.error(
        '[useConversation] Failed to restart recording after interrupt:',
        error
      )
    }
  }, [setPlaying, setRecording, triggerInterrupt])

  // 计算状态
  const canStartConversation =
    !isRecording &&
    !isPlaying &&
    isConnected &&
    (state === ConversationState.IDLE || state === ConversationState.ERROR)
  const canInterrupt = isPlaying && state === ConversationState.SPEAKING

  // TTS音频播放处理函数
  const handleTTSAudio = useCallback(
    (message: any) => {
      const { audioData, format } = message.data

      if (audioData) {
        console.log('[useConversation] Processing TTS audio for playback')

        try {
          // 将Base64数据转换为Blob
          const binaryString = atob(audioData)
          const bytes = new Uint8Array(binaryString.length)
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }
          const audioBlob = new Blob([bytes], {
            type: `audio/${format || 'mp3'}`,
          })

          console.log(
            `[useConversation] Playing TTS audio: ${audioBlob.size} bytes`
          )

          // 播放音频
          audioService.playAudio(audioBlob).catch((error: any) => {
            console.error('[useConversation] TTS playback failed:', error)
            setError({
              code: 'PLAYBACK_FAILED',
              message: '音频播放失败',
              retryable: true,
            })
          })
        } catch (error: any) {
          console.error('[useConversation] Failed to process TTS audio:', error)
          setError({
            code: 'AUDIO_PROCESSING_FAILED',
            message: '音频处理失败',
            retryable: true,
          })
        }
      }
    },
    [setError]
  )

  // 初始化和事件监听
  useEffect(() => {
    if (isInitialized.current) return
    isInitialized.current = true

    console.log('[useConversation] Initializing event handlers...')

    // WebSocket连接状态监听
    const handleConnection = (connected: boolean) => {
      setConnected(connected)
    }

    // 设置WebSocket消息处理器
    websocketService.onMessage(
      MessageType.CONNECTION_ESTABLISHED,
      handleConnectionEstablished
    )
    websocketService.onMessage(MessageType.STT_START, handleSTTStart)
    websocketService.onMessage(MessageType.STT_RESULT, handleSTTResult)
    websocketService.onMessage(MessageType.LLM_START, handleLLMStart)
    websocketService.onMessage(MessageType.LLM_RESPONSE, handleLLMResponse)
    websocketService.onMessage(MessageType.TTS_START, handleTTSStart)
    websocketService.onMessage(MessageType.TTS_RESULT, handleTTSResult)
    websocketService.onMessage(MessageType.TTS_RESULT, handleTTSAudio) // 添加TTS音频播放处理
    websocketService.onMessage(
      MessageType.TTS_UNAVAILABLE,
      handleTTSUnavailable
    )
    websocketService.onMessage(MessageType.HEARTBEAT_ACK, handleHeartbeatAck)
    websocketService.onMessage(MessageType.ERROR, handleError)

    // WebSocket连接状态监听
    websocketService.onConnection(handleConnection)

    // 音频chunk处理
    const handleAudioChunk = (chunk: Blob) => {
      console.log('[useConversation] Audio chunk received:', chunk.size)

      // 发送音频数据到服务器
      websocketService.sendAudioChunk(chunk, false)

      // 设置延迟发送结束信号
      if (audioChunkTimeoutRef.current) {
        clearTimeout(audioChunkTimeoutRef.current)
      }

      audioChunkTimeoutRef.current = setTimeout(() => {
        console.log('[useConversation] Audio chunk timeout, sending end signal')
        websocketService.sendAudioChunk(new Blob(), true)
      }, 1000) // 1秒后发送结束信号
    }

    // 录制状态变化处理
    const handleRecordingState = (recording: boolean) => {
      console.log('[useConversation] Recording state changed:', recording)
      setRecording(recording)

      if (!recording) {
        // 录制结束，发送最后一个音频块
        if (audioChunkTimeoutRef.current) {
          clearTimeout(audioChunkTimeoutRef.current)
        }
        websocketService.sendAudioChunk(new Blob(), true)
      }
    }

    // 音频播放状态处理
    const handlePlaybackState = (playing: boolean) => {
      console.log('[useConversation] Playback state changed:', playing)
      setPlaying(playing)
    }

    // 注册音频事件监听器
    audioService.onAudioChunk(handleAudioChunk)
    audioService.onRecordingState(handleRecordingState)
    audioService.onPlaybackState(handlePlaybackState)

    // 清理函数
    return () => {
      console.log('[useConversation] Cleaning up event handlers...')

      // 清理WebSocket消息处理器
      websocketService.offMessage(
        MessageType.CONNECTION_ESTABLISHED,
        handleConnectionEstablished
      )
      websocketService.offMessage(MessageType.STT_START, handleSTTStart)
      websocketService.offMessage(MessageType.STT_RESULT, handleSTTResult)
      websocketService.offMessage(MessageType.LLM_START, handleLLMStart)
      websocketService.offMessage(MessageType.LLM_RESPONSE, handleLLMResponse)
      websocketService.offMessage(MessageType.TTS_START, handleTTSStart)
      websocketService.offMessage(MessageType.TTS_RESULT, handleTTSResult)
      websocketService.offMessage(MessageType.TTS_RESULT, handleTTSAudio)
      websocketService.offMessage(
        MessageType.TTS_UNAVAILABLE,
        handleTTSUnavailable
      )
      websocketService.offMessage(MessageType.HEARTBEAT_ACK, handleHeartbeatAck)
      websocketService.offMessage(MessageType.ERROR, handleError)

      // 清理连接状态监听
      websocketService.offConnection(handleConnection)

      // 清理音频事件监听器
      audioService.offAudioChunk(handleAudioChunk)
      audioService.offRecordingState(handleRecordingState)
      audioService.offPlaybackState(handlePlaybackState)

      // 清理定时器
      if (audioChunkTimeoutRef.current) {
        clearTimeout(audioChunkTimeoutRef.current)
      }
    }
  }, [
    setConnected,
    setRecording,
    setPlaying,
    setCurrentAudioUrl,
    handleConnectionEstablished,
    handleSTTStart,
    handleSTTResult,
    handleLLMStart,
    handleLLMResponse,
    handleTTSStart,
    handleTTSResult,
    handleTTSAudio,
    handleTTSUnavailable,
    handleHeartbeatAck,
    handleError,
  ])

  return {
    // 状态
    state,
    isConnected,
    isRecording,
    isPlaying,
    currentText,
    finalText,
    aiResponse,
    error,

    // 控制方法
    connect,
    disconnect,
    startConversation,
    stopConversation,
    interrupt,

    // 状态查询
    canStartConversation,
    canInterrupt,
  }
}
