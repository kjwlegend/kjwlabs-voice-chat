/**
 * 对话Hook - 增强版
 * 管理语音对话的完整流程，支持双路径TTS和智能超时断开
 */

import { useCallback, useEffect, useRef } from "react";
import { useConversationStore } from "@/stores/conversationStore";
import { websocketService } from "@/services/websocketService";
import { audioService } from "@/services";
import { ConversationState, MessageType } from "@/types";

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

  // 新增：双路径响应状态
  immediateResponse: string;
  finalResponse: string;
  hasFinalResponse: boolean;
  patienceMessage: string;

  // 控制方法
  connect: () => Promise<void>;
  disconnect: () => void;
  startConversation: () => Promise<void>;
  stopConversation: () => void;
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
    // 新增：从store获取双路径响应状态
    immediateResponse: storeImmediateResponse,
    finalResponse: storeFinalResponse,
    hasFinalResponse: storeHasFinalResponse,
    patienceMessage: storePatienceMessage,
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
    // 新增：双路径LLM处理器
    handleLLMImmediateResponse,
    handleLLMFinalResponse,
    handleLLMPatienceUpdate,
    handleTTSStart,
    handleTTSResult,
    // 新增：双路径TTS处理器
    handleTTSImmediateStart,
    handleTTSImmediateResult,
    handleTTSFinalStart,
    handleTTSFinalResult,
    handleTTSUnavailable,
    handleHeartbeatAck,
    handleError,
    triggerInterrupt,
  } = useConversationStore();

  const isInitialized = useRef(false);
  const audioChunkTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 新增：30秒超时和用户活动检测
  const userActivityTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const INACTIVITY_TIMEOUT = 30 * 1000; // 30秒
  const isGoodbyePlaying = useRef(false);

  // 重置用户活动计时器
  const resetUserActivityTimer = useCallback(() => {
    if (userActivityTimeoutRef.current) {
      clearTimeout(userActivityTimeoutRef.current);
    }

    // 如果正在进行对话，启动30秒计时器
    if (isConnected && (isRecording || isPlaying)) {
      userActivityTimeoutRef.current = setTimeout(() => {
        console.log(
          "[useConversation] User inactive for 30 seconds, playing goodbye message"
        );
        playGoodbyeAndDisconnect();
      }, INACTIVITY_TIMEOUT);
    }
  }, [isConnected, isRecording, isPlaying]);

  // 播放告别消息并断开连接
  const playGoodbyeAndDisconnect = useCallback(async () => {
    if (isGoodbyePlaying.current) return;

    try {
      isGoodbyePlaying.current = true;
      console.log(
        "[useConversation] Playing goodbye message and disconnecting"
      );

      // 停止当前录制
      if (isRecording) {
        audioService.stopRecording();
        setRecording(false);
      }

      // 创建告别消息的TTS音频
      const goodbyeText = "检测到你已经不在啦，那我先挂啦";

      // 这里我们直接创建一个简单的语音提示
      // 在实际应用中，可以发送到后端生成TTS
      const utterance = new SpeechSynthesisUtterance(goodbyeText);
      utterance.lang = "zh-CN";
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      utterance.onend = () => {
        console.log(
          "[useConversation] Goodbye message finished, disconnecting..."
        );
        setTimeout(() => {
          // 执行断开逻辑
          if (userActivityTimeoutRef.current) {
            clearTimeout(userActivityTimeoutRef.current);
            userActivityTimeoutRef.current = null;
          }
          if (audioChunkTimeoutRef.current) {
            clearTimeout(audioChunkTimeoutRef.current);
            audioChunkTimeoutRef.current = null;
          }
          websocketService.disconnect();
          audioService.cleanup();
          isGoodbyePlaying.current = false;
        }, 1000);
      };

      utterance.onerror = () => {
        console.log(
          "[useConversation] Goodbye TTS failed, disconnecting directly"
        );
        setTimeout(() => {
          // 执行断开逻辑
          if (userActivityTimeoutRef.current) {
            clearTimeout(userActivityTimeoutRef.current);
            userActivityTimeoutRef.current = null;
          }
          if (audioChunkTimeoutRef.current) {
            clearTimeout(audioChunkTimeoutRef.current);
            audioChunkTimeoutRef.current = null;
          }
          websocketService.disconnect();
          audioService.cleanup();
          isGoodbyePlaying.current = false;
        }, 1000);
      };

      speechSynthesis.speak(utterance);
    } catch (error) {
      console.error("[useConversation] Failed to play goodbye message:", error);
      // 执行断开逻辑
      if (userActivityTimeoutRef.current) {
        clearTimeout(userActivityTimeoutRef.current);
        userActivityTimeoutRef.current = null;
      }
      if (audioChunkTimeoutRef.current) {
        clearTimeout(audioChunkTimeoutRef.current);
        audioChunkTimeoutRef.current = null;
      }
      websocketService.disconnect();
      audioService.cleanup();
      isGoodbyePlaying.current = false;
    }
  }, [isRecording, setRecording]);

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

    // 清理所有计时器
    if (userActivityTimeoutRef.current) {
      clearTimeout(userActivityTimeoutRef.current);
      userActivityTimeoutRef.current = null;
    }

    if (audioChunkTimeoutRef.current) {
      clearTimeout(audioChunkTimeoutRef.current);
      audioChunkTimeoutRef.current = null;
    }

    // 重置双路径状态 - 现在在store中管理
    isGoodbyePlaying.current = false;

    websocketService.disconnect();
    audioService.cleanup();
  }, []);

  // 开始对话
  const startConversation = useCallback(async () => {
    try {
      console.log("[useConversation] Starting conversation...");
      await audioService.startRecording();
      websocketService.startConversation();
      setRecording(true);

      // 启动用户活动检测
      resetUserActivityTimer();
    } catch (error) {
      console.error("[useConversation] Failed to start conversation:", error);
      setError({
        code: "RECORDING_FAILED",
        message: "录音失败，请检查麦克风权限",
        retryable: true,
      });
      throw error;
    }
  }, [setRecording, setError, resetUserActivityTimer]);

  // 停止对话
  const stopConversation = useCallback(() => {
    console.log("[useConversation] Stopping conversation...");
    audioService.stopRecording();
    websocketService.endConversation();
    setRecording(false);

    // 清理活动计时器
    if (userActivityTimeoutRef.current) {
      clearTimeout(userActivityTimeoutRef.current);
      userActivityTimeoutRef.current = null;
    }
  }, [setRecording]);

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

      // 重置用户活动计时器
      resetUserActivityTimer();
    } catch (error: any) {
      console.error(
        "[useConversation] Failed to restart recording after interrupt:",
        error
      );
    }
  }, [setPlaying, setRecording, triggerInterrupt, resetUserActivityTimer]);

  // 计算状态
  const canStartConversation =
    !isRecording &&
    !isPlaying &&
    isConnected &&
    !isGoodbyePlaying.current &&
    (state === ConversationState.IDLE || state === ConversationState.ERROR);
  const canInterrupt = isPlaying && state === ConversationState.SPEAKING;

  // 通用TTS音频播放处理函数
  const playTTSAudio = useCallback(
    async (audioData: string, format: string = "mp3") => {
      try {
        console.log("[useConversation] Processing TTS audio for playback");

        // 将Base64数据转换为Blob
        const binaryString = atob(audioData);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const audioBlob = new Blob([bytes], {
          type: `audio/${format}`,
        });

        console.log(
          `[useConversation] Playing TTS audio: ${audioBlob.size} bytes`
        );

        // 播放音频并重置用户活动计时器
        await audioService.playAudio(audioBlob);
        resetUserActivityTimer();
      } catch (error: any) {
        console.error("[useConversation] Failed to process TTS audio:", error);
        setError({
          code: "AUDIO_PROCESSING_FAILED",
          message: "音频处理失败",
          retryable: true,
        });
      }
    },
    [setError, resetUserActivityTimer]
  );

  // 传统TTS音频播放处理函数
  const handleTTSAudio = useCallback(
    (message: any) => {
      const { audioData, format } = message.data;
      if (audioData) {
        playTTSAudio(audioData, format);
      }
    },
    [playTTSAudio]
  );

  // 包装store中的处理器以添加用户活动检测和TTS播放
  const wrappedLLMImmediateResponse = useCallback(
    (message: any) => {
      handleLLMImmediateResponse(message);
      resetUserActivityTimer();
    },
    [handleLLMImmediateResponse, resetUserActivityTimer]
  );

  const wrappedLLMFinalResponse = useCallback(
    (message: any) => {
      handleLLMFinalResponse(message);
      resetUserActivityTimer();
    },
    [handleLLMFinalResponse, resetUserActivityTimer]
  );

  const wrappedLLMPatienceUpdate = useCallback(
    (message: any) => {
      handleLLMPatienceUpdate(message);
    },
    [handleLLMPatienceUpdate]
  );

  // 包装TTS处理器以添加音频播放功能
  const wrappedTTSImmediateResult = useCallback(
    (message: any) => {
      const { audioData, format } = message.data;
      console.log("[useConversation] TTS Immediate Result received");
      if (audioData) {
        playTTSAudio(audioData, format || "mp3");
      }
      handleTTSImmediateResult(message);
    },
    [playTTSAudio, handleTTSImmediateResult]
  );

  const wrappedTTSFinalResult = useCallback(
    (message: any) => {
      const { audioData, format } = message.data;
      console.log("[useConversation] TTS Final Result received");
      if (audioData) {
        playTTSAudio(audioData, format || "mp3");
      }
      handleTTSFinalResult(message);
    },
    [playTTSAudio, handleTTSFinalResult]
  );

  // 初始化和事件监听
  useEffect(() => {
    if (isInitialized.current) return;
    isInitialized.current = true;

    console.log("[useConversation] Initializing enhanced event handlers...");

    // WebSocket连接状态监听
    const handleConnection = (connected: boolean) => {
      setConnected(connected);
      if (!connected) {
        // 连接断开时清理计时器
        if (userActivityTimeoutRef.current) {
          clearTimeout(userActivityTimeoutRef.current);
          userActivityTimeoutRef.current = null;
        }
      }
    };

    // 设置WebSocket消息处理器
    websocketService.onMessage(
      MessageType.CONNECTION_ESTABLISHED,
      handleConnectionEstablished
    );
    websocketService.onMessage(MessageType.STT_START, handleSTTStart);
    websocketService.onMessage(MessageType.STT_RESULT, handleSTTResult);
    websocketService.onMessage(MessageType.LLM_START, handleLLMStart);
    websocketService.onMessage(MessageType.LLM_RESPONSE, handleLLMResponse);

    // 双路径LLM消息监听器
    websocketService.onMessage(
      MessageType.LLM_IMMEDIATE_RESPONSE,
      wrappedLLMImmediateResponse
    );
    websocketService.onMessage(
      MessageType.LLM_FINAL_RESPONSE,
      wrappedLLMFinalResponse
    );
    websocketService.onMessage(
      MessageType.LLM_PATIENCE_UPDATE,
      wrappedLLMPatienceUpdate
    );

    websocketService.onMessage(MessageType.TTS_START, handleTTSStart);
    websocketService.onMessage(MessageType.TTS_RESULT, handleTTSResult);
    websocketService.onMessage(MessageType.TTS_RESULT, handleTTSAudio); // 兼容传统TTS

    // 双路径TTS消息监听器
    websocketService.onMessage(
      MessageType.TTS_IMMEDIATE_RESULT,
      wrappedTTSImmediateResult
    );
    websocketService.onMessage(
      MessageType.TTS_FINAL_RESULT,
      wrappedTTSFinalResult
    );

    websocketService.onMessage(
      MessageType.TTS_UNAVAILABLE,
      handleTTSUnavailable
    );
    websocketService.onMessage(MessageType.HEARTBEAT_ACK, handleHeartbeatAck);
    websocketService.onMessage(MessageType.ERROR, handleError);

    // WebSocket连接状态监听
    websocketService.onConnection(handleConnection);

    // 音频chunk处理
    const handleAudioChunk = (chunk: Blob) => {
      console.log("[useConversation] Audio chunk received:", chunk.size);

      // 发送音频数据到服务器
      websocketService.sendAudioChunk(chunk, false);

      // 重置用户活动计时器
      resetUserActivityTimer();

      // 设置延迟发送结束信号
      if (audioChunkTimeoutRef.current) {
        clearTimeout(audioChunkTimeoutRef.current);
      }

      audioChunkTimeoutRef.current = setTimeout(() => {
        console.log(
          "[useConversation] Audio chunk timeout, sending end signal"
        );
        websocketService.sendAudioChunk(new Blob(), true);
      }, 1000); // 1秒后发送结束信号
    };

    // 录制状态变化处理
    const handleRecordingState = (recording: boolean) => {
      console.log("[useConversation] Recording state changed:", recording);
      setRecording(recording);

      if (recording) {
        // 开始录制时重置计时器
        resetUserActivityTimer();
      } else {
        // 录制结束，发送最后一个音频块
        if (audioChunkTimeoutRef.current) {
          clearTimeout(audioChunkTimeoutRef.current);
        }
        websocketService.sendAudioChunk(new Blob(), true);
      }
    };

    // 音频播放状态处理
    const handlePlaybackState = (playing: boolean) => {
      console.log("[useConversation] Playback state changed:", playing);
      setPlaying(playing);

      if (playing) {
        // 开始播放时重置计时器
        resetUserActivityTimer();
      }
    };

    // 注册音频事件监听器
    audioService.onAudioChunk(handleAudioChunk);
    audioService.onRecordingState(handleRecordingState);
    audioService.onPlaybackState(handlePlaybackState);

    // 清理函数
    return () => {
      console.log("[useConversation] Cleaning up enhanced event handlers...");

      // 清理WebSocket消息处理器
      websocketService.offMessage(
        MessageType.CONNECTION_ESTABLISHED,
        handleConnectionEstablished
      );
      websocketService.offMessage(MessageType.STT_START, handleSTTStart);
      websocketService.offMessage(MessageType.STT_RESULT, handleSTTResult);
      websocketService.offMessage(MessageType.LLM_START, handleLLMStart);
      websocketService.offMessage(MessageType.LLM_RESPONSE, handleLLMResponse);

      // 清理双路径LLM监听器
      websocketService.offMessage(
        MessageType.LLM_IMMEDIATE_RESPONSE,
        wrappedLLMImmediateResponse
      );
      websocketService.offMessage(
        MessageType.LLM_FINAL_RESPONSE,
        wrappedLLMFinalResponse
      );
      websocketService.offMessage(
        MessageType.LLM_PATIENCE_UPDATE,
        wrappedLLMPatienceUpdate
      );

      websocketService.offMessage(MessageType.TTS_START, handleTTSStart);
      websocketService.offMessage(MessageType.TTS_RESULT, handleTTSResult);
      websocketService.offMessage(MessageType.TTS_RESULT, handleTTSAudio);

      // 清理双路径TTS监听器
      websocketService.offMessage(
        MessageType.TTS_IMMEDIATE_RESULT,
        wrappedTTSImmediateResult
      );
      websocketService.offMessage(
        MessageType.TTS_FINAL_RESULT,
        wrappedTTSFinalResult
      );

      websocketService.offMessage(
        MessageType.TTS_UNAVAILABLE,
        handleTTSUnavailable
      );
      websocketService.offMessage(
        MessageType.HEARTBEAT_ACK,
        handleHeartbeatAck
      );
      websocketService.offMessage(MessageType.ERROR, handleError);

      // 清理连接状态监听
      websocketService.offConnection(handleConnection);

      // 清理音频事件监听器
      audioService.offAudioChunk(handleAudioChunk);
      audioService.offRecordingState(handleRecordingState);
      audioService.offPlaybackState(handlePlaybackState);

      // 清理定时器
      if (audioChunkTimeoutRef.current) {
        clearTimeout(audioChunkTimeoutRef.current);
      }
      if (userActivityTimeoutRef.current) {
        clearTimeout(userActivityTimeoutRef.current);
      }
    };
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
    wrappedLLMImmediateResponse,
    wrappedLLMFinalResponse,
    wrappedLLMPatienceUpdate,
    wrappedTTSImmediateResult,
    wrappedTTSFinalResult,
    resetUserActivityTimer,
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

    // 新增：双路径响应状态
    immediateResponse: storeImmediateResponse,
    finalResponse: storeFinalResponse,
    hasFinalResponse: storeHasFinalResponse,
    patienceMessage: storePatienceMessage,

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
