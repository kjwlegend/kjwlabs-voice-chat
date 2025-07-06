/**
 * 语音活动检测(VAD)自定义Hook
 * 基于@ricky0123/vad-web实现
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { VADConfig } from "@/types";

// VAD事件类型
export interface VADEvents {
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
  onVADMisfire?: () => void;
}

// VAD状态
export interface VADState {
  isListening: boolean;
  isSpeaking: boolean;
  isLoaded: boolean;
  error: string | null;
}

// Hook返回值
export interface UseVADReturn extends VADState {
  start: () => Promise<void>;
  stop: () => void;
  toggle: () => Promise<void>;
  updateConfig: (config: Partial<VADConfig>) => void;
}

// 默认VAD配置
const DEFAULT_VAD_CONFIG: VADConfig = {
  positiveSpeechThreshold: 0.8,
  negativeSpeechThreshold: 0.8 - 0.15,
  preSpeechPadFrames: 2,
  redemptionFrames: 8,
  frameSamples: 1536,
  minSpeechFrames: 4,
};

export function useVAD(
  events: VADEvents = {},
  initialConfig: Partial<VADConfig> = {}
): UseVADReturn {
  const [state, setState] = useState<VADState>({
    isListening: false,
    isSpeaking: false,
    isLoaded: false,
    error: null,
  });

  const vadRef = useRef<any>(null);
  const configRef = useRef<VADConfig>({
    ...DEFAULT_VAD_CONFIG,
    ...initialConfig,
  });
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const eventsRef = useRef(events);

  // 更新事件引用
  useEffect(() => {
    eventsRef.current = events;
  }, [events]);

  // 加载VAD模型
  const loadVAD = useCallback(async () => {
    try {
      console.log("[useVAD] Loading VAD model...");

      // 动态导入VAD库
      const { MicVAD } = await import("@ricky0123/vad-web");

      vadRef.current = await MicVAD.new({
        positiveSpeechThreshold: configRef.current.positiveSpeechThreshold,
        negativeSpeechThreshold: configRef.current.negativeSpeechThreshold,
        preSpeechPadFrames: configRef.current.preSpeechPadFrames,
        redemptionFrames: configRef.current.redemptionFrames,
        frameSamples: configRef.current.frameSamples,
        minSpeechFrames: configRef.current.minSpeechFrames,

        onSpeechStart: () => {
          console.log("[useVAD] Speech started");
          setState((prev) => ({ ...prev, isSpeaking: true }));
          eventsRef.current.onSpeechStart?.();
        },

        onSpeechEnd: (audio: Float32Array) => {
          console.log("[useVAD] Speech ended, audio length:", audio.length);
          setState((prev) => ({ ...prev, isSpeaking: false }));
          eventsRef.current.onSpeechEnd?.();
        },

        onVADMisfire: () => {
          console.log("[useVAD] VAD misfire detected");
          eventsRef.current.onVADMisfire?.();
        },
      });

      setState((prev) => ({ ...prev, isLoaded: true, error: null }));
      console.log("[useVAD] VAD model loaded successfully");
    } catch (error) {
      console.error("[useVAD] Failed to load VAD model:", error);
      setState((prev) => ({
        ...prev,
        isLoaded: false,
        error: error instanceof Error ? error.message : "Failed to load VAD",
      }));
      throw error;
    }
  }, []);

  // 开始VAD监听
  const start = useCallback(async () => {
    try {
      console.log("[useVAD] Starting VAD...");

      // 确保VAD已加载
      if (!vadRef.current) {
        await loadVAD();
      }

      // 开始监听
      await vadRef.current.start();

      setState((prev) => ({ ...prev, isListening: true, error: null }));
      console.log("[useVAD] VAD started successfully");
    } catch (error) {
      console.error("[useVAD] Failed to start VAD:", error);

      let errorMessage = "Failed to start VAD";
      if (error instanceof Error) {
        if (error.name === "NotAllowedError") {
          errorMessage = "需要麦克风权限";
        } else if (error.name === "NotFoundError") {
          errorMessage = "未找到麦克风设备";
        } else {
          errorMessage = error.message;
        }
      }

      setState((prev) => ({
        ...prev,
        isListening: false,
        error: errorMessage,
      }));
      throw error;
    }
  }, [loadVAD]);

  // 停止VAD监听
  const stop = useCallback(() => {
    try {
      console.log("[useVAD] Stopping VAD...");

      if (vadRef.current) {
        vadRef.current.pause();
      }

      // 清理媒体流
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }

      setState((prev) => ({
        ...prev,
        isListening: false,
        isSpeaking: false,
        error: null,
      }));

      console.log("[useVAD] VAD stopped successfully");
    } catch (error) {
      console.error("[useVAD] Failed to stop VAD:", error);
    }
  }, []);

  // 切换VAD状态
  const toggle = useCallback(async () => {
    if (state.isListening) {
      stop();
    } else {
      await start();
    }
  }, [state.isListening, start, stop]);

  // 更新VAD配置
  const updateConfig = useCallback(
    (newConfig: Partial<VADConfig>) => {
      console.log("[useVAD] Updating config:", newConfig);
      configRef.current = { ...configRef.current, ...newConfig };

      // 如果VAD正在运行，需要重启以应用新配置
      if (state.isListening && vadRef.current) {
        stop();
        // 延迟重启以确保完全停止
        setTimeout(() => {
          start().catch((error) => {
            console.error("[useVAD] Failed to restart with new config:", error);
          });
        }, 100);
      }
    },
    [state.isListening, start, stop]
  );

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      console.log("[useVAD] Cleaning up VAD...");
      stop();

      if (vadRef.current) {
        vadRef.current.destroy?.();
        vadRef.current = null;
      }
    };
  }, [stop]);

  // 初始化VAD模型
  useEffect(() => {
    loadVAD().catch((error) => {
      console.error("[useVAD] Initial VAD load failed:", error);
    });
  }, [loadVAD]);

  return {
    ...state,
    start,
    stop,
    toggle,
    updateConfig,
  };
}
