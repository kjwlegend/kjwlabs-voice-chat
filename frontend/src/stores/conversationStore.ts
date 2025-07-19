/**
 * 对话状态管理 - 增强版
 * 使用Zustand管理全局对话状态，支持双路径AI响应
 */

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import {
  ConversationState,
  ConversationTurn,
  PerformanceMetrics,
  STTMessageData,
  LLMResponseData,
  ErrorMessageData,
  TTSMessageData,
  WebSocketMessage,
} from "@/types";

interface ConversationStore {
  // 状态数据
  state: ConversationState;
  isConnected: boolean;
  isRecording: boolean;
  currentText: string; // 当前识别的文本
  finalText: string; // 最终确认的文本
  aiResponse: string; // AI回复文本

  // 新增：双路径响应状态
  immediateResponse: string; // 立即响应
  finalResponse: string; // 最终响应
  hasFinalResponse: boolean; // 是否有最终响应
  patienceMessage: string; // 耐心等待消息

  error: ErrorMessageData | null;

  // 对话历史
  conversationHistory: ConversationTurn[];

  // 性能数据
  metrics: PerformanceMetrics | null;

  // 音频相关
  audioChunks: Blob[];
  isPlaying: boolean;
  currentAudioUrl: string | null;

  // Actions
  setState: (newState: ConversationState) => void;
  setConnected: (connected: boolean) => void;
  setRecording: (recording: boolean) => void;
  setCurrentText: (text: string) => void;
  setFinalText: (text: string) => void;
  setAiResponse: (response: string) => void;

  // 新增：双路径响应设置
  setImmediateResponse: (response: string) => void;
  setFinalResponse: (response: string) => void;
  setHasFinalResponse: (hasFinal: boolean) => void;
  setPatienceMessage: (message: string) => void;
  clearDualPathResponses: () => void;

  setError: (error: ErrorMessageData | null) => void;
  setPlaying: (playing: boolean) => void;
  setMetrics: (metrics: PerformanceMetrics) => void;
  setCurrentAudioUrl: (url: string | null) => void;

  // 对话管理
  addConversationTurn: (turn: ConversationTurn) => void;
  clearConversation: () => void;

  // 音频管理
  addAudioChunk: (chunk: Blob) => void;
  clearAudioChunks: () => void;

  // 重置状态
  reset: () => void;

  // 消息处理器
  handleConnectionEstablished: (message: WebSocketMessage) => void;
  handleSTTStart: (message: WebSocketMessage) => void;
  handleSTTResult: (message: WebSocketMessage) => void;
  handleLLMStart: (message: WebSocketMessage) => void;
  handleLLMResponse: (message: WebSocketMessage) => void;

  // 新增：双路径LLM处理器
  handleLLMImmediateResponse: (message: WebSocketMessage) => void;
  handleLLMFinalResponse: (message: WebSocketMessage) => void;
  handleLLMPatienceUpdate: (message: WebSocketMessage) => void;

  handleTTSStart: (message: WebSocketMessage) => void;
  handleTTSResult: (message: WebSocketMessage) => void;

  // 新增：双路径TTS处理器
  handleTTSImmediateStart: (message: WebSocketMessage) => void;
  handleTTSImmediateResult: (message: WebSocketMessage) => void;
  handleTTSFinalStart: (message: WebSocketMessage) => void;
  handleTTSFinalResult: (message: WebSocketMessage) => void;

  handleTTSUnavailable: (message: WebSocketMessage) => void;
  handleHeartbeatAck: (message: WebSocketMessage) => void;
  handleError: (message: WebSocketMessage) => void;

  // 兼容性方法
  handleSTTData: (data: STTMessageData) => void;
  triggerInterrupt: () => void;
}

// 初始状态
const initialState = {
  state: ConversationState.IDLE,
  isConnected: false,
  isRecording: false,
  currentText: "",
  finalText: "",
  aiResponse: "",

  // 双路径响应初始状态
  immediateResponse: "",
  finalResponse: "",
  hasFinalResponse: false,
  patienceMessage: "",

  error: null,
  conversationHistory: [],
  metrics: null,
  audioChunks: [],
  isPlaying: false,
  currentAudioUrl: null,
};

export const useConversationStore = create<ConversationStore>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // 基础状态设置
      setState: (newState: ConversationState) => {
        console.log(
          `[ConversationStore] State change: ${get().state} -> ${newState}`
        );
        set({ state: newState });
      },

      setConnected: (connected: boolean) => {
        console.log(`[ConversationStore] Connection: ${connected}`);
        set({ isConnected: connected });

        // 连接断开时重置状态
        if (!connected) {
          set({
            state: ConversationState.DISCONNECTED,
            isRecording: false,
            isPlaying: false,
            error: null,
            // 清理双路径响应状态
            immediateResponse: "",
            finalResponse: "",
            hasFinalResponse: false,
            patienceMessage: "",
          });
        } else {
          // 连接成功时设置为空闲状态
          set({
            state: ConversationState.IDLE,
            error: null,
          });
        }
      },

      setRecording: (recording: boolean) => {
        console.log(`[ConversationStore] Recording: ${recording}`);
        set({ isRecording: recording });

        if (recording) {
          set({
            state: ConversationState.LISTENING,
            currentText: "",
            error: null,
          });
        }
      },

      setCurrentText: (text: string) => {
        set({ currentText: text });
      },

      setFinalText: (text: string) => {
        console.log(`[ConversationStore] Final text: ${text}`);
        set({
          finalText: text,
          currentText: text,
        });
      },

      setAiResponse: (response: string) => {
        console.log(
          `[ConversationStore] AI response: ${response.substring(0, 50)}...`
        );
        set({
          aiResponse: response,
        });
      },

      // 新增：双路径响应设置方法
      setImmediateResponse: (response: string) => {
        console.log(
          `[ConversationStore] Immediate response: ${response.substring(
            0,
            50
          )}...`
        );
        set({ immediateResponse: response });
      },

      setFinalResponse: (response: string) => {
        console.log(
          `[ConversationStore] Final response: ${response.substring(0, 50)}...`
        );
        set({
          finalResponse: response,
          hasFinalResponse: true,
        });
      },

      setHasFinalResponse: (hasFinal: boolean) => {
        set({ hasFinalResponse: hasFinal });
      },

      setPatienceMessage: (message: string) => {
        console.log(`[ConversationStore] Patience message: ${message}`);
        set({ patienceMessage: message });
      },

      clearDualPathResponses: () => {
        console.log("[ConversationStore] Clearing dual path responses");
        set({
          immediateResponse: "",
          finalResponse: "",
          hasFinalResponse: false,
          patienceMessage: "",
        });
      },

      setError: (error: ErrorMessageData | null) => {
        if (error) {
          console.error(`[ConversationStore] Error: ${error.message}`);
          set({
            error,
            state: ConversationState.ERROR,
            isRecording: false,
            isPlaying: false,
          });
        } else {
          set({ error: null });
        }
      },

      setPlaying: (playing: boolean) => {
        console.log(`[ConversationStore] Playing: ${playing}`);
        set({ isPlaying: playing });

        if (playing) {
          set({ state: ConversationState.SPEAKING });
        } else if (get().state === ConversationState.SPEAKING) {
          // 播放结束，返回空闲状态
          set({ state: ConversationState.IDLE });
        }
      },

      setMetrics: (metrics: PerformanceMetrics) => {
        console.log(`[ConversationStore] Metrics updated:`, metrics);
        set({ metrics });
      },

      setCurrentAudioUrl: (url: string | null) => {
        set({ currentAudioUrl: url });
      },

      // 对话管理
      addConversationTurn: (turn: ConversationTurn) => {
        console.log(`[ConversationStore] Adding conversation turn: ${turn.id}`);
        set((state) => ({
          conversationHistory: [...state.conversationHistory, turn],
        }));
      },

      clearConversation: () => {
        console.log(`[ConversationStore] Clearing conversation history`);
        set({ conversationHistory: [] });
      },

      // 音频管理
      addAudioChunk: (chunk: Blob) => {
        set((state) => ({
          audioChunks: [...state.audioChunks, chunk],
        }));
      },

      clearAudioChunks: () => {
        set({ audioChunks: [] });
      },

      // 重置状态
      reset: () => {
        console.log("[ConversationStore] Resetting state");
        set(initialState);
      },

      // 消息处理器
      handleConnectionEstablished: (message: WebSocketMessage) => {
        console.log("[ConversationStore] Connection established", message.data);
        set({
          isConnected: true,
          state: ConversationState.IDLE,
          error: null,
        });
      },

      handleSTTStart: (message: WebSocketMessage) => {
        console.log("[ConversationStore] STT started", message.data);
        set({
          state: ConversationState.LISTENING,
          currentText: "",
        });
      },

      handleSTTResult: (message: WebSocketMessage) => {
        console.log("[ConversationStore] STT result", message.data);
        const data = message.data;

        if (data.type === "final") {
          set({
            finalText: data.text,
            currentText: data.text,
            state: ConversationState.THINKING,
            isRecording: false,
          });
        } else if (data.type === "partial") {
          set({
            currentText: data.text,
          });
        }
      },

      handleLLMStart: (message: WebSocketMessage) => {
        console.log("[ConversationStore] LLM started", message.data);
        set({
          state: ConversationState.THINKING,
          // 清理之前的双路径响应
          immediateResponse: "",
          finalResponse: "",
          hasFinalResponse: false,
          patienceMessage: "",
        });
      },

      handleLLMResponse: (message: WebSocketMessage) => {
        console.log("[ConversationStore] LLM response", message.data);
        const data = message.data;

        set({
          aiResponse: data.text,
          state: ConversationState.THINKING, // 等待TTS
        });
      },

      // 新增：双路径LLM处理器
      handleLLMImmediateResponse: (message: WebSocketMessage) => {
        console.log("[ConversationStore] LLM immediate response", message.data);
        const data = message.data;
        set({
          immediateResponse: data.text,
          state: ConversationState.THINKING,
        });
      },

      handleLLMFinalResponse: (message: WebSocketMessage) => {
        console.log("[ConversationStore] LLM final response", message.data);
        const data = message.data;
        set({
          finalResponse: data.text,
          hasFinalResponse: true,
          state: ConversationState.THINKING, // 等待TTS
        });
      },

      handleLLMPatienceUpdate: (message: WebSocketMessage) => {
        console.log("[ConversationStore] LLM patience update", message.data);
        const data = message.data;
        set({
          patienceMessage: data.message,
        });
      },

      handleTTSStart: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS started", message.data);
        set({
          state: ConversationState.SPEAKING,
        });
      },

      handleTTSResult: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS result", message.data);
        const data = message.data;

        // 创建对话回合记录
        const turn: ConversationTurn = {
          id: Date.now().toString(),
          userInput: get().finalText,
          aiResponse:
            get().aiResponse || get().finalResponse || get().immediateResponse,
          timestamp: Date.now(),
          duration: 0, // 可以后续计算
        };

        get().addConversationTurn(turn);

        // TTS音频数据将在音频服务中处理
      },

      // 新增：双路径TTS处理器
      handleTTSImmediateStart: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS immediate start", message.data);
        set({
          state: ConversationState.SPEAKING,
        });
      },

      handleTTSImmediateResult: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS immediate result", message.data);
        // 立即TTS完成，但保持speaking状态，等待最终TTS
      },

      handleTTSFinalStart: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS final start", message.data);
        set({
          state: ConversationState.SPEAKING,
        });
      },

      handleTTSFinalResult: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS final result", message.data);

        // 创建对话回合记录（使用最终响应）
        const turn: ConversationTurn = {
          id: Date.now().toString(),
          userInput: get().finalText,
          aiResponse: get().finalResponse || get().immediateResponse,
          timestamp: Date.now(),
          duration: 0,
        };

        get().addConversationTurn(turn);
      },

      handleTTSUnavailable: (message: WebSocketMessage) => {
        console.log("[ConversationStore] TTS unavailable", message.data);
        set({
          state: ConversationState.IDLE,
          error: {
            code: "TTS_UNAVAILABLE",
            message: message.data.message || "TTS服务不可用",
            retryable: false,
          },
        });
      },

      handleHeartbeatAck: (message: WebSocketMessage) => {
        console.log("[ConversationStore] Heartbeat acknowledged", message.data);
        // 可以用于监控连接状态
      },

      handleError: (message: WebSocketMessage) => {
        console.error("[ConversationStore] Received error", message.data);
        const errorData = message.data;

        set({
          error: errorData,
          state: ConversationState.ERROR,
          isRecording: false,
          isPlaying: false,
        });
      },

      // 兼容性方法
      handleSTTData: (data: STTMessageData) => {
        console.log("[ConversationStore] STT data (legacy)", data);

        if (data.isFinal) {
          set({
            finalText: data.text,
            currentText: data.text,
            state: ConversationState.THINKING,
            isRecording: false,
          });
        } else {
          set({
            currentText: data.text,
          });
        }
      },

      triggerInterrupt: () => {
        console.log("[ConversationStore] Interrupt triggered");
        set({
          state: ConversationState.IDLE,
          isPlaying: false,
          // 清理双路径响应状态
          immediateResponse: "",
          finalResponse: "",
          hasFinalResponse: false,
          patienceMessage: "",
        });
      },
    }),
    {
      name: "conversation-store",
    }
  )
);
