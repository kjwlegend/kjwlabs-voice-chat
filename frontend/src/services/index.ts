/**
 * 服务层索引文件
 * 统一导出所有服务
 */

import { WebSocketService } from './websocketService'
import { AudioService } from './audioService'
import { appConfig } from '../../config'

// 创建服务实例
export const websocketService = new WebSocketService(appConfig.wsUrl)
export const audioService = new AudioService()

// 导出类型和接口
export * from './websocketService'
export * from './audioService'

// 导出配置信息
export { appConfig }
