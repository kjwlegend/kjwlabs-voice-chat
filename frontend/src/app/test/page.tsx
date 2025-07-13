'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { audioService } from '@/services'
import { websocketService } from '@/services/websocketService'
import { MessageType } from '@/types'

/**
 * 语音对话测试页面
 * 提供每个步骤的单独测试功能
 */
export default function TestPage() {
  // 录制相关状态
  const [isRecording, setIsRecording] = useState(false)
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null)

  // 播放相关状态
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null)

  // WebSocket相关状态
  const [isConnected, setIsConnected] = useState(false)
  const [connectionLog, setConnectionLog] = useState<string[]>([])

  // STT相关状态
  const [sttText, setSttText] = useState<string>('')
  const [sttStatus, setSttStatus] = useState<string>('待发送')
  const [sttLogs, setSttLogs] = useState<string[]>([])

  // LLM相关状态
  const [llmResponse, setLlmResponse] = useState<string>('')
  const [llmStatus, setLlmStatus] = useState<string>('待处理')
  const [llmLogs, setLlmLogs] = useState<string[]>([])

  // 双路径LLM响应状态
  const [immediateResponse, setImmediateResponse] = useState<string>('')
  const [finalResponse, setFinalResponse] = useState<string>('')
  const [hasFinalResponse, setHasFinalResponse] = useState<boolean>(false)
  const [patienceMessage, setPatienceMessage] = useState<string>('')

  // TTS相关状态
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null)
  const [ttsStatus, setTtsStatus] = useState<string>('待生成')
  const [ttsLogs, setTtsLogs] = useState<string[]>([])

  // 双路径TTS状态
  const [immediateAudioUrl, setImmediateAudioUrl] = useState<string | null>(
    null
  )
  const [finalAudioUrl, setFinalAudioUrl] = useState<string | null>(null)
  const [immediateTtsStatus, setImmediateTtsStatus] = useState<string>('待生成')
  const [finalTtsStatus, setFinalTtsStatus] = useState<string>('待生成')

  // 调试信息
  const [debugInfo, setDebugInfo] = useState<any[]>([])

  // 添加日志函数
  const addLog = (category: string, message: string) => {
    const timestamp = new Date().toLocaleTimeString()
    const logEntry = `[${timestamp}] ${message}`

    if (category === 'connection') {
      setConnectionLog((prev) => [...prev, logEntry])
    } else if (category === 'stt') {
      setSttLogs((prev) => [...prev, logEntry])
    } else if (category === 'llm') {
      setLlmLogs((prev) => [...prev, logEntry])
    } else if (category === 'tts') {
      setTtsLogs((prev) => [...prev, logEntry])
    }
  }

  // 初始化WebSocket连接
  useEffect(() => {
    const initWebSocket = async () => {
      try {
        addLog('connection', '正在连接WebSocket...')
        await websocketService.connect()
        setIsConnected(true)
        addLog('connection', 'WebSocket连接成功')
      } catch (error) {
        addLog('connection', `WebSocket连接失败: ${error}`)
      }
    }

    // 设置WebSocket消息监听
    const handleSTTStart = (message: any) => {
      addLog('stt', 'STT开始处理')
      setSttStatus('处理中')
    }

    const handleSTTResult = (message: any) => {
      const data = message.data
      addLog('stt', `STT结果: ${data.text}`)
      setSttText(data.text)
      setSttStatus('完成')
    }

    const handleLLMStart = (message: any) => {
      addLog('llm', 'LLM开始处理')
      setLlmStatus('思考中')
    }

    const handleLLMResponse = (message: any) => {
      const data = message.data
      addLog('llm', `LLM回复: ${data.text}`)
      setLlmResponse(data.text)
      setLlmStatus('完成')

      // 清空双路径响应状态，避免UI冲突
      setImmediateResponse('')
      setFinalResponse('')
      setHasFinalResponse(false)
      setPatienceMessage('')
    }

    // 新增：双路径LLM响应处理器
    const handleLLMImmediateResponse = (message: any) => {
      const data = message.data
      addLog('llm', `立即响应: ${data.text}`)
      setImmediateResponse(data.text)
      setLlmStatus('立即响应完成')

      // 清空传统响应状态，避免UI冲突
      setLlmResponse('')
    }

    const handleLLMFinalResponse = (message: any) => {
      const data = message.data
      addLog('llm', `最终响应: ${data.text}`)
      setFinalResponse(data.text)
      setHasFinalResponse(true)
      setLlmStatus('最终响应完成')

      // 清空传统响应状态，避免UI冲突
      setLlmResponse('')
    }

    const handleLLMPatienceUpdate = (message: any) => {
      const data = message.data
      addLog('llm', `耐心等待: ${data.message}`)
      setPatienceMessage(data.message)
    }

    const handleTTSStart = (message: any) => {
      addLog('tts', 'TTS开始生成')
      setTtsStatus('生成中')
    }

    const handleTTSResult = (message: any) => {
      const data = message.data
      addLog('tts', `TTS音频生成完成: ${data.audioData?.length || 0} bytes`)

      if (data.audioData) {
        try {
          // 将Base64数据转换为Blob
          const binaryString = atob(data.audioData)
          const bytes = new Uint8Array(binaryString.length)
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }
          const audioBlob = new Blob([bytes], {
            type: `audio/${data.format || 'mp3'}`,
          })
          const audioUrl = URL.createObjectURL(audioBlob)
          setTtsAudioUrl(audioUrl)
          setTtsStatus('完成')

          // 清空双路径TTS状态，避免UI冲突
          setImmediateAudioUrl(null)
          setFinalAudioUrl(null)
          setImmediateTtsStatus('待生成')
          setFinalTtsStatus('待生成')
        } catch (error) {
          addLog('tts', `TTS音频处理失败: ${error}`)
          setTtsStatus('失败')
        }
      }
    }

    // 新增：双路径TTS处理器
    const handleTTSImmediateStart = (message: any) => {
      addLog('tts', '即时TTS开始生成')
      setImmediateTtsStatus('生成中')

      // 清空传统TTS状态，避免UI冲突
      setTtsAudioUrl(null)
      setTtsStatus('待生成')
    }

    const handleTTSImmediateResult = (message: any) => {
      const data = message.data
      addLog('tts', `即时TTS音频生成完成: ${data.audioData?.length || 0} bytes`)

      if (data.audioData) {
        try {
          const binaryString = atob(data.audioData)
          const bytes = new Uint8Array(binaryString.length)
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }
          const audioBlob = new Blob([bytes], {
            type: `audio/${data.format || 'mp3'}`,
          })
          const audioUrl = URL.createObjectURL(audioBlob)
          setImmediateAudioUrl(audioUrl)
          setImmediateTtsStatus('完成')

          // 确保传统TTS状态已清空
          setTtsAudioUrl(null)
          setTtsStatus('待生成')
        } catch (error) {
          addLog('tts', `即时TTS音频处理失败: ${error}`)
          setImmediateTtsStatus('失败')
        }
      }
    }

    const handleTTSFinalStart = (message: any) => {
      addLog('tts', '最终TTS开始生成')
      setFinalTtsStatus('生成中')
    }

    const handleTTSFinalResult = (message: any) => {
      const data = message.data
      addLog('tts', `最终TTS音频生成完成: ${data.audioData?.length || 0} bytes`)

      if (data.audioData) {
        try {
          const binaryString = atob(data.audioData)
          const bytes = new Uint8Array(binaryString.length)
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }
          const audioBlob = new Blob([bytes], {
            type: `audio/${data.format || 'mp3'}`,
          })
          const audioUrl = URL.createObjectURL(audioBlob)
          setFinalAudioUrl(audioUrl)
          setFinalTtsStatus('完成')

          // 确保传统TTS状态已清空
          setTtsAudioUrl(null)
          setTtsStatus('待生成')
        } catch (error) {
          addLog('tts', `最终TTS音频处理失败: ${error}`)
          setFinalTtsStatus('失败')
        }
      }
    }

    const handleError = (message: any) => {
      const data = message.data
      addLog('connection', `错误: ${data.message}`)
      setDebugInfo((prev) => [
        ...prev,
        { type: 'error', data, timestamp: Date.now() },
      ])
    }

    // 注册消息监听器
    websocketService.onMessage(MessageType.STT_START, handleSTTStart)
    websocketService.onMessage(MessageType.STT_RESULT, handleSTTResult)
    websocketService.onMessage(MessageType.LLM_START, handleLLMStart)
    websocketService.onMessage(MessageType.LLM_RESPONSE, handleLLMResponse)

    // 双路径LLM消息监听器
    websocketService.onMessage(
      MessageType.LLM_IMMEDIATE_RESPONSE,
      handleLLMImmediateResponse
    )
    websocketService.onMessage(
      MessageType.LLM_FINAL_RESPONSE,
      handleLLMFinalResponse
    )
    websocketService.onMessage(
      MessageType.LLM_PATIENCE_UPDATE,
      handleLLMPatienceUpdate
    )

    websocketService.onMessage(MessageType.TTS_START, handleTTSStart)
    websocketService.onMessage(MessageType.TTS_RESULT, handleTTSResult)

    // 双路径TTS消息监听器
    websocketService.onMessage(
      MessageType.TTS_IMMEDIATE_START,
      handleTTSImmediateStart
    )
    websocketService.onMessage(
      MessageType.TTS_IMMEDIATE_RESULT,
      handleTTSImmediateResult
    )
    websocketService.onMessage(MessageType.TTS_FINAL_START, handleTTSFinalStart)
    websocketService.onMessage(
      MessageType.TTS_FINAL_RESULT,
      handleTTSFinalResult
    )

    websocketService.onMessage(MessageType.ERROR, handleError)

    // WebSocket连接状态监听
    websocketService.onConnection((connected) => {
      setIsConnected(connected)
      addLog('connection', `连接状态: ${connected ? '已连接' : '已断开'}`)
    })

    // 初始化连接
    initWebSocket()

    // 清理函数
    return () => {
      websocketService.offMessage(MessageType.STT_START, handleSTTStart)
      websocketService.offMessage(MessageType.STT_RESULT, handleSTTResult)
      websocketService.offMessage(MessageType.LLM_START, handleLLMStart)
      websocketService.offMessage(MessageType.LLM_RESPONSE, handleLLMResponse)

      // 清理双路径LLM监听器
      websocketService.offMessage(
        MessageType.LLM_IMMEDIATE_RESPONSE,
        handleLLMImmediateResponse
      )
      websocketService.offMessage(
        MessageType.LLM_FINAL_RESPONSE,
        handleLLMFinalResponse
      )
      websocketService.offMessage(
        MessageType.LLM_PATIENCE_UPDATE,
        handleLLMPatienceUpdate
      )

      websocketService.offMessage(MessageType.TTS_START, handleTTSStart)
      websocketService.offMessage(MessageType.TTS_RESULT, handleTTSResult)

      // 清理双路径TTS监听器
      websocketService.offMessage(
        MessageType.TTS_IMMEDIATE_START,
        handleTTSImmediateStart
      )
      websocketService.offMessage(
        MessageType.TTS_IMMEDIATE_RESULT,
        handleTTSImmediateResult
      )
      websocketService.offMessage(
        MessageType.TTS_FINAL_START,
        handleTTSFinalStart
      )
      websocketService.offMessage(
        MessageType.TTS_FINAL_RESULT,
        handleTTSFinalResult
      )

      websocketService.offMessage(MessageType.ERROR, handleError)

      // 清理音频URL
      if (currentAudioUrl) {
        URL.revokeObjectURL(currentAudioUrl)
      }
      if (ttsAudioUrl) {
        URL.revokeObjectURL(ttsAudioUrl)
      }
      if (immediateAudioUrl) {
        URL.revokeObjectURL(immediateAudioUrl)
      }
      if (finalAudioUrl) {
        URL.revokeObjectURL(finalAudioUrl)
      }
    }
  }, [])

  // 开始录制
  const startRecording = async () => {
    try {
      addLog('connection', '开始录制音频...')
      setRecordedBlob(null)
      setRecordingDuration(0)

      // 清理之前的音频URL
      if (currentAudioUrl) {
        URL.revokeObjectURL(currentAudioUrl)
        setCurrentAudioUrl(null)
      }

      // 初始化并开始录制
      await audioService.initializeRecording()
      await audioService.startRecording()
      setIsRecording(true)

      // 开始计时
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1)
      }, 1000)

      addLog('connection', '录制已开始')
    } catch (error) {
      addLog('connection', `录制失败: ${error}`)
    }
  }

  // 停止录制
  const stopRecording = async () => {
    try {
      addLog('connection', '停止录制...')

      // 清除计时器
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current)
        recordingTimerRef.current = null
      }

      // 停止录制并获取录制的音频数据
      const recordedAudio = await audioService.stopRecording()
      setRecordedBlob(recordedAudio)

      // 创建音频URL供播放
      const audioUrl = URL.createObjectURL(recordedAudio)
      setCurrentAudioUrl(audioUrl)

      setIsRecording(false)

      addLog('connection', `录制已停止，音频大小: ${recordedAudio.size} bytes`)
    } catch (error) {
      addLog('connection', `停止录制失败: ${error}`)
      setIsRecording(false)
    }
  }

  // 播放录制的音频
  const playRecordedAudio = async () => {
    if (!recordedBlob) return

    try {
      addLog('connection', '播放录制的音频...')
      setIsPlaying(true)

      await audioService.playAudio(recordedBlob)
      setIsPlaying(false)
      addLog('connection', '播放完成')
    } catch (error) {
      addLog('connection', `播放失败: ${error}`)
      setIsPlaying(false)
    }
  }

  // 发送音频到后端
  const sendAudioToBackend = async () => {
    if (!recordedBlob || !isConnected) return

    try {
      addLog('stt', '发送音频到后端...')
      setSttStatus('发送中')

      // 发送音频数据
      await websocketService.sendAudioChunk(recordedBlob, true)

      addLog('stt', '音频已发送')
    } catch (error) {
      addLog('stt', `发送失败: ${error}`)
      setSttStatus('失败')
    }
  }

  // 播放TTS音频
  const playTtsAudio = async () => {
    if (!ttsAudioUrl) return

    try {
      addLog('tts', '播放TTS音频...')
      setIsPlaying(true)

      const audio = new Audio(ttsAudioUrl)
      audio.onended = () => {
        setIsPlaying(false)
        addLog('tts', 'TTS音频播放完成')
      }
      audio.onerror = (error) => {
        setIsPlaying(false)
        addLog('tts', `TTS音频播放失败: ${error}`)
      }

      await audio.play()
    } catch (error) {
      addLog('tts', `播放TTS音频失败: ${error}`)
      setIsPlaying(false)
    }
  }

  // 播放即时TTS音频
  const playImmediateTtsAudio = async () => {
    if (!immediateAudioUrl) return

    try {
      addLog('tts', '播放即时TTS音频...')
      setIsPlaying(true)

      const audio = new Audio(immediateAudioUrl)
      audio.onended = () => {
        setIsPlaying(false)
        addLog('tts', '即时TTS音频播放完成')
      }
      audio.onerror = (error) => {
        setIsPlaying(false)
        addLog('tts', `即时TTS音频播放失败: ${error}`)
      }

      await audio.play()
    } catch (error) {
      addLog('tts', `播放即时TTS音频失败: ${error}`)
      setIsPlaying(false)
    }
  }

  // 播放最终TTS音频
  const playFinalTtsAudio = async () => {
    if (!finalAudioUrl) return

    try {
      addLog('tts', '播放最终TTS音频...')
      setIsPlaying(true)

      const audio = new Audio(finalAudioUrl)
      audio.onended = () => {
        setIsPlaying(false)
        addLog('tts', '最终TTS音频播放完成')
      }
      audio.onerror = (error) => {
        setIsPlaying(false)
        addLog('tts', `最终TTS音频播放失败: ${error}`)
      }

      await audio.play()
    } catch (error) {
      addLog('tts', `播放最终TTS音频失败: ${error}`)
      setIsPlaying(false)
    }
  }

  // 清除所有状态
  const clearAll = () => {
    setRecordedBlob(null)
    setRecordingDuration(0)
    setSttText('')
    setSttStatus('待发送')
    setSttLogs([])
    setLlmResponse('')
    setLlmStatus('待处理')
    setLlmLogs([])

    // 清理双路径LLM状态
    setImmediateResponse('')
    setFinalResponse('')
    setHasFinalResponse(false)
    setPatienceMessage('')

    setTtsAudioUrl(null)
    setTtsStatus('待生成')
    setTtsLogs([])

    // 清理双路径TTS状态
    setImmediateAudioUrl(null)
    setFinalAudioUrl(null)
    setImmediateTtsStatus('待生成')
    setFinalTtsStatus('待生成')

    setDebugInfo([])

    // 清理所有音频URL
    if (currentAudioUrl) {
      URL.revokeObjectURL(currentAudioUrl)
      setCurrentAudioUrl(null)
    }
    if (ttsAudioUrl) {
      URL.revokeObjectURL(ttsAudioUrl)
    }
    if (immediateAudioUrl) {
      URL.revokeObjectURL(immediateAudioUrl)
    }
    if (finalAudioUrl) {
      URL.revokeObjectURL(finalAudioUrl)
    }
  }

  // 设置录制状态回调
  useEffect(() => {
    const handleRecordingState = (isRecording: boolean) => {
      addLog('connection', `录制状态改变: ${isRecording ? '开始' : '停止'}`)
    }

    audioService.onRecordingState(handleRecordingState)

    return () => {
      audioService.offRecordingState(handleRecordingState)
    }
  }, [])

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">语音对话测试页面</h1>
        <p className="text-gray-600">逐步测试语音对话的每个环节</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. 录制音频 */}
        <Card>
          <CardHeader>
            <CardTitle>1. 录制音频</CardTitle>
            <CardDescription>测试音频录制功能</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <Button
                onClick={startRecording}
                disabled={isRecording}
                variant={isRecording ? 'secondary' : 'default'}
              >
                {isRecording ? '录制中...' : '开始录制'}
              </Button>
              <Button
                onClick={stopRecording}
                disabled={!isRecording}
                variant="destructive"
              >
                停止录制
              </Button>
            </div>
            {isRecording && (
              <div className="text-sm text-gray-500">
                录制时长: {recordingDuration}秒
              </div>
            )}
            {recordedBlob && (
              <div className="text-sm text-green-600">
                录制完成: {recordedBlob.size} bytes
              </div>
            )}
          </CardContent>
        </Card>

        {/* 2. 播放录制内容 */}
        <Card>
          <CardHeader>
            <CardTitle>2. 播放录制内容</CardTitle>
            <CardDescription>测试音频播放功能</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={playRecordedAudio}
              disabled={!recordedBlob || isPlaying}
              variant="outline"
            >
              {isPlaying ? '播放中...' : '播放录制内容'}
            </Button>
            {currentAudioUrl && (
              <audio controls className="w-full">
                <source src={currentAudioUrl} type="audio/wav" />
                您的浏览器不支持音频播放
              </audio>
            )}
          </CardContent>
        </Card>

        {/* 3. WebSocket连接状态 */}
        <Card>
          <CardHeader>
            <CardTitle>3. WebSocket连接</CardTitle>
            <CardDescription>测试后端连接状态</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={`flex items-center space-x-2 ${
                isConnected ? 'text-green-600' : 'text-red-600'
              }`}
            >
              <div
                className={`w-3 h-3 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              ></div>
              <span>{isConnected ? '已连接' : '未连接'}</span>
            </div>
            <div className="text-sm max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">
              {connectionLog.map((log, index) => (
                <div key={index} className="text-xs">
                  {log}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 4. 发送音频到后端 */}
        <Card>
          <CardHeader>
            <CardTitle>4. 发送音频到后端</CardTitle>
            <CardDescription>测试音频上传功能</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={sendAudioToBackend}
              disabled={!recordedBlob || !isConnected}
              variant="default"
            >
              发送到后端
            </Button>
            <div className="text-sm text-gray-600">状态: {sttStatus}</div>
          </CardContent>
        </Card>

        {/* 5. STT结果 */}
        <Card>
          <CardHeader>
            <CardTitle>5. STT语音识别结果</CardTitle>
            <CardDescription>显示语音转文字结果</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-3 bg-gray-50 rounded min-h-[60px]">
              {sttText || '等待识别结果...'}
            </div>
            <div className="text-sm max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">
              {sttLogs.map((log, index) => (
                <div key={index} className="text-xs">
                  {log}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 6. LLM回复 */}
        <Card>
          <CardHeader>
            <CardTitle>6. LLM AI回复（双路径）</CardTitle>
            <CardDescription>显示AI生成的立即响应和最终响应</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 双路径响应模式 */}
            {(immediateResponse || finalResponse || hasFinalResponse) && (
              <>
                {/* 立即响应 */}
                <div className="border rounded p-3">
                  <div className="text-sm font-medium text-blue-600 mb-2">
                    ⚡ 立即响应 (Path A)
                  </div>
                  <div className="p-3 bg-blue-50 rounded min-h-[40px]">
                    {immediateResponse || '等待立即响应...'}
                  </div>
                </div>

                {/* 耐心等待消息 */}
                {patienceMessage && (
                  <div className="text-xs text-orange-600 bg-orange-50 p-2 rounded">
                    ⏳ {patienceMessage}
                  </div>
                )}

                {/* 最终响应 */}
                {hasFinalResponse && (
                  <div className="border rounded p-3">
                    <div className="text-sm font-medium text-green-600 mb-2">
                      🔧 最终响应 (Path B - 工具调用完成)
                    </div>
                    <div className="p-3 bg-green-50 rounded min-h-[40px]">
                      {finalResponse}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* 传统响应模式 (仅在无双路径时显示) */}
            {llmResponse &&
              !immediateResponse &&
              !finalResponse &&
              !hasFinalResponse && (
                <div className="border rounded p-3">
                  <div className="text-sm font-medium text-gray-600 mb-2">
                    📝 传统响应
                  </div>
                  <div className="p-3 bg-gray-50 rounded min-h-[40px]">
                    {llmResponse}
                  </div>
                </div>
              )}

            <div className="text-sm text-gray-600">状态: {llmStatus}</div>
            <div className="text-sm max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">
              {llmLogs.map((log, index) => (
                <div key={index} className="text-xs">
                  {log}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 7. TTS音频播放 */}
        <Card>
          <CardHeader>
            <CardTitle>7. TTS语音合成（双路径）</CardTitle>
            <CardDescription>
              测试立即TTS和最终TTS音频生成和播放
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 双路径TTS音频模式 */}
            {(immediateAudioUrl || finalAudioUrl) && (
              <>
                {/* 即时TTS音频 */}
                <div className="border rounded p-3">
                  <div className="text-sm font-medium text-blue-600 mb-2">
                    ⚡ 即时TTS音频 (Path A)
                  </div>
                  <div className="space-y-2">
                    <Button
                      onClick={playImmediateTtsAudio}
                      disabled={!immediateAudioUrl || isPlaying}
                      variant="outline"
                      size="sm"
                    >
                      {isPlaying ? '播放中...' : '播放即时音频'}
                    </Button>
                    <div className="text-xs text-gray-600">
                      状态: {immediateTtsStatus}
                    </div>
                    {immediateAudioUrl && (
                      <audio controls className="w-full">
                        <source src={immediateAudioUrl} type="audio/mp3" />
                        您的浏览器不支持音频播放
                      </audio>
                    )}
                  </div>
                </div>

                {/* 最终TTS音频 */}
                {finalAudioUrl && (
                  <div className="border rounded p-3">
                    <div className="text-sm font-medium text-green-600 mb-2">
                      🔧 最终TTS音频 (Path B)
                    </div>
                    <div className="space-y-2">
                      <Button
                        onClick={playFinalTtsAudio}
                        disabled={!finalAudioUrl || isPlaying}
                        variant="outline"
                        size="sm"
                      >
                        {isPlaying ? '播放中...' : '播放最终音频'}
                      </Button>
                      <div className="text-xs text-gray-600">
                        状态: {finalTtsStatus}
                      </div>
                      <audio controls className="w-full">
                        <source src={finalAudioUrl} type="audio/mp3" />
                        您的浏览器不支持音频播放
                      </audio>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* 传统单一TTS音频（兼容模式） */}
            {ttsAudioUrl && !immediateAudioUrl && !finalAudioUrl && (
              <div className="border rounded p-3">
                <div className="text-sm font-medium text-gray-600 mb-2">
                  📝 传统TTS音频
                </div>
                <div className="space-y-2">
                  <Button
                    onClick={playTtsAudio}
                    disabled={!ttsAudioUrl || isPlaying}
                    variant="outline"
                    size="sm"
                  >
                    {isPlaying ? '播放中...' : '播放TTS音频'}
                  </Button>
                  <div className="text-xs text-gray-600">状态: {ttsStatus}</div>
                  <audio controls className="w-full">
                    <source src={ttsAudioUrl} type="audio/mp3" />
                    您的浏览器不支持音频播放
                  </audio>
                </div>
              </div>
            )}

            <div className="text-sm max-h-32 overflow-y-auto bg-gray-50 p-2 rounded">
              {ttsLogs.map((log, index) => (
                <div key={index} className="text-xs">
                  {log}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 8. 调试信息 */}
        <Card>
          <CardHeader>
            <CardTitle>8. 调试信息</CardTitle>
            <CardDescription>显示详细的调试信息</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={clearAll} variant="destructive" size="sm">
              清除所有状态
            </Button>
            <div className="text-sm max-h-48 overflow-y-auto bg-gray-50 p-2 rounded">
              {debugInfo.map((info, index) => (
                <div key={index} className="text-xs mb-2">
                  <strong>{info.type}:</strong>
                  <pre className="mt-1 text-xs">
                    {JSON.stringify(info.data, null, 2)}
                  </pre>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
