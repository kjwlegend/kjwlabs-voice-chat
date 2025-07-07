/**
 * 服务层索引文件
 * 统一导出所有服务
 */

import { WebSocketService } from './websocketService'
import { AudioService } from './audioService'
import { appConfig } from '../../config'

// 生成唯一的客户端ID
function generateClientId(): string {
  return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// 创建WebSocket URL (包含客户端ID)
const clientId = generateClientId()
const wsUrl = `${appConfig.wsUrl}/${clientId}`

// 创建服务实例
export const websocketService = new WebSocketService(wsUrl)
export const audioService = new AudioService()

// 导出类型和接口
export * from './websocketService'
export * from './audioService'

// 导出配置信息
export { appConfig, clientId }
