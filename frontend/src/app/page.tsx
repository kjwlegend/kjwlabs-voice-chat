"use client";

import { useEffect, useState } from "react";
import Script from "next/script";
import { Mic, Phone, PhoneOff, AlertCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useConversation } from "@/hooks/useConversation";
import { ConversationState } from "@/types";

export default function VoiceApp() {
  const {
    state,
    isConnected,
    isRecording,
    isPlaying,
    currentText,
    finalText,
    aiResponse,
    error,
    connect,
    disconnect,
    startConversation,
    stopConversation,
    interrupt,
    canStartConversation,
    canInterrupt,
  } = useConversation();

  const [isInitialized, setIsInitialized] = useState(false);
  const [isElevenLabsLoaded, setIsElevenLabsLoaded] = useState(false);

  // 初始化WebSocket连接
  useEffect(() => {
    const initializeConnection = async () => {
      try {
        console.log("[VoiceApp] Initializing WebSocket connection...");
        await connect();
        setIsInitialized(true);
        console.log("[VoiceApp] WebSocket connection established");
      } catch (error) {
        console.error("[VoiceApp] Failed to initialize connection:", error);
      }
    };

    if (!isInitialized) {
      initializeConnection();
    }

    // 清理函数
    return () => {
      if (isInitialized) {
        disconnect();
      }
    };
  }, [connect, disconnect, isInitialized]);

  const handleCallToggle = async () => {
    if (canStartConversation) {
      try {
        console.log("[VoiceApp] Starting conversation...");
        await startConversation();
      } catch (error) {
        console.error("[VoiceApp] Failed to start conversation:", error);
      }
    } else if (isRecording || isPlaying) {
      try {
        console.log("[VoiceApp] Stopping conversation...");
        await stopConversation();
      } catch (error) {
        console.error("[VoiceApp] Failed to stop conversation:", error);
      }
    }
  };

  const handleInterrupt = () => {
    if (canInterrupt) {
      console.log("[VoiceApp] Interrupting AI...");
      interrupt();
    }
  };

  const getStateText = () => {
    switch (state) {
      case ConversationState.IDLE:
        return "准备就绪";
      case ConversationState.LISTENING:
        return "正在聆听...";
      case ConversationState.THINKING:
        return "正在思考...";
      case ConversationState.SPEAKING:
        return "正在说话...";
      case ConversationState.ERROR:
        return "发生错误";
      case ConversationState.DISCONNECTED:
        return "连接断开";
      default:
        return "准备就绪";
    }
  };

  const getStateColor = () => {
    switch (state) {
      case ConversationState.IDLE:
        return "text-blue-400";
      case ConversationState.LISTENING:
        return "text-green-400";
      case ConversationState.THINKING:
        return "text-yellow-400";
      case ConversationState.SPEAKING:
        return "text-purple-400";
      case ConversationState.ERROR:
        return "text-red-400";
      case ConversationState.DISCONNECTED:
        return "text-gray-400";
      default:
        return "text-blue-400";
    }
  };

  const getGlowColor = () => {
    switch (state) {
      case ConversationState.IDLE:
        return "shadow-blue-500/50";
      case ConversationState.LISTENING:
        return "shadow-green-500/50";
      case ConversationState.THINKING:
        return "shadow-yellow-500/50";
      case ConversationState.SPEAKING:
        return "shadow-purple-500/50";
      case ConversationState.ERROR:
        return "shadow-red-500/50";
      case ConversationState.DISCONNECTED:
        return "shadow-gray-500/50";
      default:
        return "shadow-blue-500/50";
    }
  };

  const isCallActive =
    isRecording || isPlaying || state === ConversationState.THINKING;

  return (
    <>
      {/* Load ElevenLabs script */}
      <Script
        src="https://unpkg.com/@elevenlabs/convai-widget-embed"
        strategy="lazyOnload"
        onLoad={() => {
          console.log("[ElevenLabs] Widget script loaded successfully");
          setIsElevenLabsLoaded(true);
        }}
        onError={(e) => {
          console.error("[ElevenLabs] Failed to load widget script:", e);
        }}
      />

      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex flex-col items-center justify-center p-6">
        {/* 背景装饰 */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/20 rounded-full blur-3xl"></div>
        </div>

        <div className="relative z-10 text-center space-y-8">
          {/* LOGO */}
          <div className="space-y-4">
            <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
              KJW Labs
            </h1>
            <div className="w-32 h-1 bg-gradient-to-r from-blue-400 to-purple-400 mx-auto rounded-full"></div>
          </div>

          {/* 连接状态指示 */}
          <div className="flex items-center justify-center space-x-2 text-sm">
            {isConnected ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-green-400">已连接</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-red-400">连接中...</span>
              </>
            )}
          </div>

          {/* 状态指示器 */}
          <div className="space-y-6">
            <div
              className={`inline-flex items-center space-x-3 px-6 py-3 rounded-full bg-black/30 backdrop-blur-sm border border-white/10 ${getGlowColor()} shadow-2xl`}
            >
              <div
                className={`w-3 h-3 rounded-full ${
                  state === ConversationState.LISTENING ||
                  state === ConversationState.THINKING ||
                  state === ConversationState.SPEAKING
                    ? `${getStateColor().replace("text-", "bg-")} animate-pulse`
                    : getStateColor().replace("text-", "bg-")
                }`}
              ></div>
              <span className={`text-lg font-medium ${getStateColor()}`}>
                {getStateText()}
              </span>
            </div>

            {/* 音频波形动画 (仅在聆听和说话时显示) */}
            {(state === ConversationState.LISTENING ||
              state === ConversationState.SPEAKING) && (
              <div className="flex items-center justify-center space-x-1">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className={`w-1 bg-gradient-to-t ${
                      state === ConversationState.LISTENING
                        ? "from-green-400 to-green-600"
                        : "from-purple-400 to-purple-600"
                    } rounded-full animate-pulse`}
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

          {/* 文本显示区域 */}
          <div className="space-y-4 max-w-2xl mx-auto">
            {/* 当前识别文本 */}
            {currentText && (
              <div className="bg-black/20 backdrop-blur-sm rounded-lg p-4 border border-white/10">
                <p className="text-sm text-gray-400 mb-2">识别中...</p>
                <p className="text-white">{currentText}</p>
              </div>
            )}

            {/* 最终识别文本 */}
            {finalText && finalText !== currentText && (
              <div className="bg-green-900/20 backdrop-blur-sm rounded-lg p-4 border border-green-500/30">
                <p className="text-sm text-green-400 mb-2">您说：</p>
                <p className="text-white">{finalText}</p>
              </div>
            )}

            {/* AI回复 */}
            {aiResponse && (
              <div className="bg-purple-900/20 backdrop-blur-sm rounded-lg p-4 border border-purple-500/30">
                <p className="text-sm text-purple-400 mb-2">AI回复：</p>
                <p className="text-white">{aiResponse}</p>
              </div>
            )}

            {/* 错误显示 */}
            {error && (
              <div className="bg-red-900/20 backdrop-blur-sm rounded-lg p-4 border border-red-500/30">
                <p className="text-sm text-red-400 mb-2">错误：</p>
                <p className="text-white">{error.message}</p>
                {error.retryable && (
                  <p className="text-sm text-gray-400 mt-2">请重试</p>
                )}
              </div>
            )}
          </div>

          {/* 控制按钮区域 */}
          <div className="space-y-6">
            {/* 主要通话按钮 */}
            <div className="flex items-center justify-center space-x-4">
              <Button
                onClick={handleCallToggle}
                disabled={!isConnected}
                size="lg"
                className={`w-24 h-24 rounded-full text-white font-semibold text-lg transition-all duration-300 transform hover:scale-110 ${
                  isCallActive
                    ? "bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 shadow-red-500/50"
                    : "bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-blue-500/50"
                } shadow-2xl disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {isCallActive ? (
                  <PhoneOff className="w-8 h-8" />
                ) : (
                  <Phone className="w-8 h-8" />
                )}
              </Button>

              {/* 打断按钮 */}
              {canInterrupt && (
                <Button
                  onClick={handleInterrupt}
                  size="lg"
                  className="w-16 h-16 rounded-full bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 shadow-orange-500/50 shadow-2xl transition-all duration-300 transform hover:scale-110"
                >
                  <Mic className="w-6 h-6" />
                </Button>
              )}
            </div>

            <div className="space-y-2">
              <p className="text-gray-300 text-sm">
                {!isConnected
                  ? "正在连接服务器..."
                  : isCallActive
                  ? "点击结束通话"
                  : "点击开始通话"}
              </p>
              {canInterrupt && (
                <p className="text-orange-300 text-xs">点击橙色按钮可打断AI</p>
              )}
            </div>
          </div>

          {/* ElevenLabs Convai Widget */}
          {isElevenLabsLoaded && (
            <div className="mt-8">
              <elevenlabs-convai agent-id="agent_01jz8nd957f10asdth3sybnfdm"></elevenlabs-convai>
            </div>
          )}

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
            {isConnected && (
              <div className="flex items-center justify-center space-x-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-green-400">服务已就绪</span>
              </div>
            )}
            {isElevenLabsLoaded && (
              <div className="flex items-center justify-center space-x-2">
                <CheckCircle className="w-4 h-4 text-blue-400" />
                <span className="text-blue-400">对话 组件已加载</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
