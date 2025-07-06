/**
 * 对话管理自定义Hook
 * 提供完整的对话功能接口
 */

import { useCallback, useEffect, useRef } from "react";
import { useConversationStore } from "@/stores";
import { websocketService, audioService } from "@/services";
import { MessageType, ConversationState } from "@/types";

export interface UseConversationReturn {
  // 状态
  state: ConversationState;
  isConnected: boolean;
  isRecording: boolean;
  isPlaying: boolean;
  currentText: string;
  finalText: string;
  aiResponse: string;
  error: any;

  // 控制方法
  connect: () => Promise<void>;
  disconnect: () => void;
  startConversation: () => Promise<void>;
  stopConversation: () => Promise<void>;
  interrupt: () => void;

  // 状态查询
  canStartConversation: boolean;
  canInterrupt: boolean;
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
    handleSTTData,
    handleLLMResponse,
    setError,
    triggerInterrupt,
  } = useConversationStore();

  const isInitialized = useRef(false);
  const vadTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 连接WebSocket
  const connect = useCallback(async () => {
    try {
      console.log("[useConversation] Connecting to WebSocket...");
      await websocketService.connect();
      console.log("[useConversation] WebSocket connected successfully");
    } catch (error) {
      console.error("[useConversation] Failed to connect:", error);
      setError({
        code: "CONNECTION_FAILED",
        message: "连接失败，请检查网络",
        retryable: true,
      });
      throw error;
    }
  }, [setError]);

  // 断开连接
  const disconnect = useCallback(() => {
    console.log("[useConversation] Disconnecting...");
    websocketService.disconnect();
    audioService.cleanup();
  }, []);

  // 开始对话
  const startConversation = useCallback(async () => {
    try {
      console.log("[useConversation] Starting conversation...");

      // 1. 初始化音频录制
      await audioService.initializeRecording();

      // 2. 开始录制
      audioService.startRecording();
      setRecording(true);

      console.log("[useConversation] Conversation started successfully");
    } catch (error) {
      console.error("[useConversation] Failed to start conversation:", error);

      if (error instanceof Error && error.name === "NotAllowedError") {
        setError({
          code: "PERMISSION_DENIED",
          message: "需要麦克风权限才能开始对话",
          retryable: false,
        });
      } else {
        setError({
          code: "START_FAILED",
          message: "启动对话失败，请重试",
          retryable: true,
        });
      }

      throw error;
    }
  }, [setRecording, setError]);

  // 停止对话
  const stopConversation = useCallback(async () => {
    try {
      console.log("[useConversation] Stopping conversation...");

      // 1. 停止录制
      if (audioService.getRecordingState() === "recording") {
        await audioService.stopRecording();
      }
      setRecording(false);

      // 2. 停止播放
      if (audioService.isPlaying()) {
        audioService.stopAudio();
      }
      setPlaying(false);

      console.log("[useConversation] Conversation stopped successfully");
    } catch (error) {
      console.error("[useConversation] Failed to stop conversation:", error);
    }
  }, [setRecording, setPlaying]);

  // 中断AI说话
  const interrupt = useCallback(() => {
    console.log("[useConversation] Interrupting AI...");

    // 1. 发送中断信号到后端
    websocketService.sendInterrupt();

    // 2. 停止本地音频播放
    audioService.stopAudio();
    setPlaying(false);

    // 3. 更新状态
    triggerInterrupt();

    // 4. 重新开始录制
    try {
      audioService.startRecording();
      setRecording(true);
    } catch (error) {
      console.error(
        "[useConversation] Failed to restart recording after interrupt:",
        error
      );
    }
  }, [setPlaying, setRecording, triggerInterrupt]);

  // 计算状态
  const canStartConversation =
    !isRecording &&
    !isPlaying &&
    isConnected &&
    (state === ConversationState.IDLE || state === ConversationState.ERROR);
  const canInterrupt = isPlaying && state === ConversationState.SPEAKING;

  // 初始化和事件监听
  useEffect(() => {
    if (isInitialized.current) return;
    isInitialized.current = true;

    console.log("[useConversation] Initializing event handlers...");

    // WebSocket连接状态监听
    const handleConnection = (connected: boolean) => {
      setConnected(connected);
    };

    // STT消息处理
    const handleSTTMessage = (message: any) => {
      handleSTTData(message.data);
    };

    // LLM响应处理
    const handleLLMMessage = (message: any) => {
      handleLLMResponse(message.data);
    };

    // TTS音频处理
    const handleTTSMessage = (message: any) => {
      const { audioData, isLast } = message.data;

      if (audioData) {
        // 播放TTS音频
        audioService.playAudio(audioData).catch((error) => {
          console.error("[useConversation] TTS playback failed:", error);
        });
      }

      if (isLast) {
        setPlaying(false);
      }
    };

    // 错误消息处理
    const handleErrorMessage = (message: any) => {
      setError(message.data);
    };

    // 音频块发送
    const handleAudioChunk = (chunk: Blob) => {
      if (websocketService.isConnected()) {
        websocketService.sendAudioChunk(chunk);
      }
    };

    // 录制状态变化
    const handleRecordingState = (recording: boolean) => {
      setRecording(recording);

      if (!recording) {
        // 录制结束，检测静音
        vadTimeoutRef.current = setTimeout(() => {
          // 如果静音超过一定时间，发送结束信号
          if (websocketService.isConnected()) {
            websocketService.sendMessage(MessageType.AUDIO_END, {});
          }
        }, 1000); // 1秒静音后发送结束信号
      } else {
        // 开始录制，清除静音检测
        if (vadTimeoutRef.current) {
          clearTimeout(vadTimeoutRef.current);
          vadTimeoutRef.current = null;
        }
      }
    };

    // 播放状态变化
    const handlePlaybackState = (playing: boolean) => {
      setPlaying(playing);
    };

    // 注册事件监听器
    websocketService.onConnection(handleConnection);
    websocketService.onMessage(MessageType.STT_PARTIAL, handleSTTMessage);
    websocketService.onMessage(MessageType.STT_FINAL, handleSTTMessage);
    websocketService.onMessage(MessageType.LLM_RESPONSE, handleLLMMessage);
    websocketService.onMessage(MessageType.TTS_CHUNK, handleTTSMessage);
    websocketService.onMessage(MessageType.ERROR, handleErrorMessage);

    audioService.onAudioChunk(handleAudioChunk);
    audioService.onRecordingState(handleRecordingState);
    audioService.onPlaybackState(handlePlaybackState);

    // 清理函数
    return () => {
      console.log("[useConversation] Cleaning up event handlers...");

      websocketService.offConnection(handleConnection);
      websocketService.offMessage(MessageType.STT_PARTIAL, handleSTTMessage);
      websocketService.offMessage(MessageType.STT_FINAL, handleSTTMessage);
      websocketService.offMessage(MessageType.LLM_RESPONSE, handleLLMMessage);
      websocketService.offMessage(MessageType.TTS_CHUNK, handleTTSMessage);
      websocketService.offMessage(MessageType.ERROR, handleErrorMessage);

      audioService.offAudioChunk(handleAudioChunk);
      audioService.offRecordingState(handleRecordingState);
      audioService.offPlaybackState(handlePlaybackState);

      if (vadTimeoutRef.current) {
        clearTimeout(vadTimeoutRef.current);
      }
    };
  }, [
    setConnected,
    setRecording,
    setPlaying,
    setError,
    handleSTTData,
    handleLLMResponse,
    triggerInterrupt,
  ]);

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
  };
}
