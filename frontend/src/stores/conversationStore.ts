/**
 * 对话状态管理
 * 使用Zustand管理全局对话状态
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
} from "@/types";

interface ConversationStore {
  // 状态数据
  state: ConversationState;
  isConnected: boolean;
  isRecording: boolean;
  currentText: string; // 当前识别的文本
  finalText: string; // 最终确认的文本
  aiResponse: string; // AI回复文本
  error: ErrorMessageData | null;

  // 对话历史
  conversationHistory: ConversationTurn[];

  // 性能数据
  metrics: PerformanceMetrics | null;

  // 音频相关
  audioChunks: Blob[];
  isPlaying: boolean;

  // Actions
  setState: (newState: ConversationState) => void;
  setConnected: (connected: boolean) => void;
  setRecording: (recording: boolean) => void;
  setCurrentText: (text: string) => void;
  setFinalText: (text: string) => void;
  setAiResponse: (response: string) => void;
  setError: (error: ErrorMessageData | null) => void;
  setPlaying: (playing: boolean) => void;
  setMetrics: (metrics: PerformanceMetrics) => void;

  // 对话管理
  addConversationTurn: (turn: ConversationTurn) => void;
  clearConversation: () => void;

  // 音频管理
  addAudioChunk: (chunk: Blob) => void;
  clearAudioChunks: () => void;

  // 重置状态
  reset: () => void;

  // 处理STT数据
  handleSTTData: (data: STTMessageData) => void;

  // 处理LLM响应
  handleLLMResponse: (data: LLMResponseData) => void;

  // 触发中断
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
  error: null,
  conversationHistory: [],
  metrics: null,
  audioChunks: [],
  isPlaying: false,
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
          state: ConversationState.THINKING,
        });
      },

      setAiResponse: (response: string) => {
        console.log(
          `[ConversationStore] AI response: ${response.substring(0, 50)}...`
        );
        set({
          aiResponse: response,
          state: ConversationState.SPEAKING,
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

        if (!playing && get().state === ConversationState.SPEAKING) {
          // 播放结束，返回空闲状态
          set({ state: ConversationState.IDLE });
        }
      },

      setMetrics: (metrics: PerformanceMetrics) => {
        console.log(`[ConversationStore] Metrics updated:`, metrics);
        set({ metrics });
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

      // 重置所有状态
      reset: () => {
        console.log(`[ConversationStore] Resetting all state`);
        set(initialState);
      },

      // STT数据处理
      handleSTTData: (data: STTMessageData) => {
        if (data.isFinal) {
          get().setFinalText(data.text);
        } else {
          get().setCurrentText(data.text);
        }
      },

      // LLM响应处理
      handleLLMResponse: (data: LLMResponseData) => {
        get().setAiResponse(data.text);

        // 如果有工具调用，可以在这里处理
        if (data.needsToolCall && data.toolCalls) {
          console.log(
            `[ConversationStore] Tool calls detected:`,
            data.toolCalls
          );
        }
      },

      // 触发中断
      triggerInterrupt: () => {
        console.log(`[ConversationStore] Triggering interrupt`);
        const currentState = get().state;

        // 只在AI说话时才能中断
        if (currentState === ConversationState.SPEAKING) {
          set({
            state: ConversationState.LISTENING,
            isPlaying: false,
            aiResponse: "",
          });
        }
      },
    }),
    {
      name: "conversation-store",
      enabled: process.env.NODE_ENV === "development",
    }
  )
);
