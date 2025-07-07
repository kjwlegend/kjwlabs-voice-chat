/**
 * WebSocket服务
 * 管理与后端的WebSocket连接和消息处理
 */

import {
  WebSocketMessage,
  MessageType,
  ConversationState,
  AudioMessageData,
  STTMessageData,
  LLMResponseData,
  TTSMessageData,
  ErrorMessageData,
  StateChangeData,
} from '@/types'

export type MessageHandler = (message: WebSocketMessage) => void

export class WebSocketService {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectDelay: number = 1000
  private heartbeatInterval: NodeJS.Timeout | null = null
  private isManualClose: boolean = false

  // 事件处理器
  private messageHandlers: Map<MessageType, MessageHandler[]> = new Map()
  private connectionHandlers: Array<(connected: boolean) => void> = []

  constructor(url: string) {
    this.url = url
    console.log('[WebSocketService] Initialized with URL:', url)
  }

  /**
   * 建立WebSocket连接
   */
  async connect(): Promise<boolean> {
    return new Promise((resolve, reject) => {
      try {
        console.log('[WebSocketService] Attempting to connect...')
        this.isManualClose = false
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('[WebSocketService] Connected successfully')
          this.reconnectAttempts = 0
          this.startHeartbeat()
          this.notifyConnectionChange(true)
          resolve(true)
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event)
        }

        this.ws.onclose = (event) => {
          console.log(
            '[WebSocketService] Connection closed:',
            event.code,
            event.reason
          )
          this.stopHeartbeat()
          this.notifyConnectionChange(false)

          if (
            !this.isManualClose &&
            this.reconnectAttempts < this.maxReconnectAttempts
          ) {
            this.attemptReconnect()
          }
        }

        this.ws.onerror = (error) => {
          console.error('[WebSocketService] Connection error:', error)
          reject(error)
        }

        // 连接超时
        setTimeout(() => {
          if (this.ws?.readyState !== WebSocket.OPEN) {
            reject(new Error('Connection timeout'))
          }
        }, 10000)
      } catch (error) {
        console.error('[WebSocketService] Failed to create connection:', error)
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    console.log('[WebSocketService] Disconnecting...')
    this.isManualClose = true
    this.stopHeartbeat()

    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect')
      this.ws = null
    }
  }

  /**
   * 发送消息
   */
  sendMessage(type: MessageType, data: any): void {
    if (!this.isConnected()) {
      console.warn('[WebSocketService] Cannot send message: not connected')
      return
    }

    const message: WebSocketMessage = {
      type,
      data,
      timestamp: Date.now(),
      id: this.generateMessageId(),
    }

    try {
      this.ws!.send(JSON.stringify(message))
      console.log(`[WebSocketService] Sent message:`, {
        type,
        dataSize: JSON.stringify(data).length,
      })
    } catch (error) {
      console.error('[WebSocketService] Failed to send message:', error)
    }
  }

  /**
   * 发送音频数据
   */
  async sendAudioChunk(
    audioData: ArrayBuffer | Blob,
    isLast: boolean = false
  ): Promise<void> {
    try {
      let processedData: string

      // 将音频数据转换为Base64字符串
      if (audioData instanceof Blob) {
        // 将Blob转换为ArrayBuffer，然后转为Base64
        const arrayBuffer = await audioData.arrayBuffer()
        const uint8Array = new Uint8Array(arrayBuffer)
        const binaryString = Array.from(uint8Array)
          .map((byte) => String.fromCharCode(byte))
          .join('')
        processedData = btoa(binaryString)
      } else if (audioData instanceof ArrayBuffer) {
        // 直接将ArrayBuffer转为Base64
        const uint8Array = new Uint8Array(audioData)
        const binaryString = Array.from(uint8Array)
          .map((byte) => String.fromCharCode(byte))
          .join('')
        processedData = btoa(binaryString)
      } else {
        console.error('[WebSocketService] Unsupported audio data type')
        return
      }

      const data: AudioMessageData = {
        audioData: processedData, // 现在是Base64字符串
        isLast,
        format: 'webm',
        sampleRate: 16000,
      }

      this.sendMessage(MessageType.AUDIO_CHUNK, data)
      console.log(
        `[WebSocketService] Sent audio chunk: ${processedData.length} bytes (base64)`
      )
    } catch (error) {
      console.error('[WebSocketService] Failed to send audio chunk:', error)
    }
  }

  /**
   * 发送中断信号
   */
  sendInterrupt(): void {
    console.log('[WebSocketService] Sending interrupt signal')
    this.sendMessage(MessageType.INTERRUPT, {})
  }

  /**
   * 添加消息处理器
   */
  onMessage(type: MessageType, handler: MessageHandler): void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, [])
    }
    this.messageHandlers.get(type)!.push(handler)
  }

  /**
   * 移除消息处理器
   */
  offMessage(type: MessageType, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(type)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  /**
   * 添加连接状态处理器
   */
  onConnection(handler: (connected: boolean) => void): void {
    this.connectionHandlers.push(handler)
  }

  /**
   * 移除连接状态处理器
   */
  offConnection(handler: (connected: boolean) => void): void {
    const index = this.connectionHandlers.indexOf(handler)
    if (index > -1) {
      this.connectionHandlers.splice(index, 1)
    }
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取连接状态
   */
  getReadyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED
  }

  // 私有方法

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data)
      console.log(`[WebSocketService] Received message:`, {
        type: message.type,
      })

      // 触发对应的处理器
      const handlers = this.messageHandlers.get(message.type)
      if (handlers) {
        handlers.forEach((handler) => {
          try {
            handler(message)
          } catch (error) {
            console.error('[WebSocketService] Message handler error:', error)
          }
        })
      }
    } catch (error) {
      console.error('[WebSocketService] Failed to parse message:', error)
    }
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(
      `[WebSocketService] Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`
    )

    setTimeout(() => {
      this.connect().catch((error) => {
        console.error('[WebSocketService] Reconnect failed:', error)
      })
    }, delay)
  }

  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.sendMessage(MessageType.HEARTBEAT, { timestamp: Date.now() })
      }
    }, 30000) // 30秒心跳
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  private notifyConnectionChange(connected: boolean): void {
    this.connectionHandlers.forEach((handler) => {
      try {
        handler(connected)
      } catch (error) {
        console.error('[WebSocketService] Connection handler error:', error)
      }
    })
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}

// 创建单例实例
const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
export const websocketService = new WebSocketService(wsUrl)
