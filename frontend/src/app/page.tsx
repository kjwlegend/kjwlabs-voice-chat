"use client"

import { useState } from "react"
import { Mic, Phone, PhoneOff } from "lucide-react"
import { Button } from "@/components/ui/button"

type CallState = "ready" | "listening" | "thinking" | "speaking"

export default function VoiceApp() {
  const [callState, setCallState] = useState<CallState>("ready")
  const [isCallActive, setIsCallActive] = useState(false)

  const handleCallToggle = () => {
    if (!isCallActive) {
      // 开始通话
      setIsCallActive(true)
      setCallState("listening")

      // 模拟状态变化
      setTimeout(() => setCallState("thinking"), 3000)
      setTimeout(() => setCallState("speaking"), 5000)
      setTimeout(() => setCallState("listening"), 8000)
    } else {
      // 结束通话
      setIsCallActive(false)
      setCallState("ready")
    }
  }

  const getStateText = () => {
    switch (callState) {
      case "ready":
        return "准备就绪"
      case "listening":
        return "正在聆听..."
      case "thinking":
        return "正在思考..."
      case "speaking":
        return "正在说话..."
      default:
        return "准备就绪"
    }
  }

  const getStateColor = () => {
    switch (callState) {
      case "ready":
        return "text-blue-400"
      case "listening":
        return "text-green-400"
      case "thinking":
        return "text-yellow-400"
      case "speaking":
        return "text-purple-400"
      default:
        return "text-blue-400"
    }
  }

  const getGlowColor = () => {
    switch (callState) {
      case "ready":
        return "shadow-blue-500/50"
      case "listening":
        return "shadow-green-500/50"
      case "thinking":
        return "shadow-yellow-500/50"
      case "speaking":
        return "shadow-purple-500/50"
      default:
        return "shadow-blue-500/50"
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex flex-col items-center justify-center p-6">
      {/* 背景装饰 */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 text-center space-y-12">
        {/* LOGO */}
        <div className="space-y-4">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
            KJW Labs
          </h1>
          <div className="w-32 h-1 bg-gradient-to-r from-blue-400 to-purple-400 mx-auto rounded-full"></div>
        </div>

        {/* 状态指示器 */}
        <div className="space-y-6">
          <div
            className={`inline-flex items-center space-x-3 px-6 py-3 rounded-full bg-black/30 backdrop-blur-sm border border-white/10 ${getGlowColor()} shadow-2xl`}
          >
            <div
              className={`w-3 h-3 rounded-full ${callState === "listening" ? "bg-green-400 animate-pulse" : callState === "thinking" ? "bg-yellow-400 animate-pulse" : callState === "speaking" ? "bg-purple-400 animate-pulse" : "bg-blue-400"}`}
            ></div>
            <span className={`text-lg font-medium ${getStateColor()}`}>{getStateText()}</span>
          </div>

          {/* 音频波形动画 (仅在聆听和说话时显示) */}
          {(callState === "listening" || callState === "speaking") && (
            <div className="flex items-center justify-center space-x-1">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className={`w-1 bg-gradient-to-t ${callState === "listening" ? "from-green-400 to-green-600" : "from-purple-400 to-purple-600"} rounded-full animate-pulse`}
                  style={{
                    height: `${Math.random() * 30 + 10}px`,
                    animationDelay: `${i * 0.1}s`,
                    animationDuration: "0.8s",
                  }}
                ></div>
              ))}
            </div>
          )}
        </div>

        {/* 通话按钮 */}
        <div className="space-y-4">
          <Button
            onClick={handleCallToggle}
            size="lg"
            className={`w-24 h-24 rounded-full text-white font-semibold text-lg transition-all duration-300 transform hover:scale-110 ${
              isCallActive
                ? "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-red-500/50"
                : "bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-blue-500/50"
            } shadow-2xl`}
          >
            {isCallActive ? <PhoneOff className="w-8 h-8" /> : <Phone className="w-8 h-8" />}
          </Button>

          <p className="text-gray-300 text-sm">{isCallActive ? "点击结束通话" : "点击开始通话"}</p>
        </div>

        {/* 功能提示 */}
        <div className="max-w-md mx-auto space-y-3 text-gray-400 text-sm">
          <div className="flex items-center justify-center space-x-2">
            <Mic className="w-4 h-4" />
            <span>支持实时语音交互</span>
          </div>
          <div className="flex items-center justify-center space-x-2">
            <div className="w-4 h-4 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full"></div>
            <span>AI 智能助手随时待命</span>
          </div>
        </div>
      </div>
    </div>
  )
}
