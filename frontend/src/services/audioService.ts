/**
 * 音频处理服务
 * 管理音频录制、播放和VAD功能
 */

import { AudioDevice, VADConfig } from "@/types";

export interface AudioRecorderOptions {
  sampleRate?: number;
  audioBitsPerSecond?: number;
  mimeType?: string;
  timeslice?: number;
}

export interface AudioPlayerOptions {
  volume?: number;
  autoplay?: boolean;
}

export type AudioChunkCallback = (chunk: Blob) => void;
export type RecordingStateCallback = (isRecording: boolean) => void;
export type PlaybackStateCallback = (isPlaying: boolean) => void;

export class AudioService {
  private mediaRecorder: MediaRecorder | null = null;
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private audioChunks: Blob[] = [];
  private currentAudio: HTMLAudioElement | null = null;

  // 回调函数
  private audioChunkCallbacks: AudioChunkCallback[] = [];
  private recordingStateCallbacks: RecordingStateCallback[] = [];
  private playbackStateCallbacks: PlaybackStateCallback[] = [];

  // 配置
  private defaultRecorderOptions: AudioRecorderOptions = {
    sampleRate: 16000,
    audioBitsPerSecond: 16000,
    mimeType: "audio/webm;codecs=opus",
    timeslice: 200, // 200ms 分片
  };

  private defaultPlayerOptions: AudioPlayerOptions = {
    volume: 1.0,
    autoplay: true,
  };

  constructor() {
    console.log("[AudioService] Initialized");
  }

  /**
   * 获取音频设备列表
   */
  async getAudioDevices(): Promise<AudioDevice[]> {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices
        .filter(
          (device) =>
            device.kind === "audioinput" || device.kind === "audiooutput"
        )
        .map((device) => ({
          deviceId: device.deviceId,
          label:
            device.label || `${device.kind} - ${device.deviceId.slice(0, 8)}`,
          kind: device.kind as "audioinput" | "audiooutput",
          groupId: device.groupId,
        }));
    } catch (error) {
      console.error("[AudioService] Failed to get audio devices:", error);
      throw error;
    }
  }

  /**
   * 检查浏览器音频支持
   */
  checkAudioSupport(): {
    mediaRecorder: boolean;
    audioContext: boolean;
    getUserMedia: boolean;
  } {
    return {
      mediaRecorder: typeof MediaRecorder !== "undefined",
      audioContext:
        typeof AudioContext !== "undefined" ||
        typeof (window as any).webkitAudioContext !== "undefined",
      getUserMedia: typeof navigator.mediaDevices?.getUserMedia !== "undefined",
    };
  }

  /**
   * 请求麦克风权限并初始化录制
   */
  async initializeRecording(
    deviceId?: string,
    options?: AudioRecorderOptions
  ): Promise<void> {
    try {
      console.log("[AudioService] Initializing recording...");

      // 请求音频权限
      const constraints: MediaStreamConstraints = {
        audio: deviceId ? { deviceId: { exact: deviceId } } : true,
        video: false,
      };

      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      console.log("[AudioService] Media stream obtained");

      // 创建音频上下文
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext ||
          (window as any).webkitAudioContext)();
        console.log("[AudioService] Audio context created");
      }

      // 配置MediaRecorder
      const recorderOptions = { ...this.defaultRecorderOptions, ...options };

      // 检查MIME类型支持
      if (!MediaRecorder.isTypeSupported(recorderOptions.mimeType!)) {
        console.warn(
          "[AudioService] MIME type not supported, falling back to default"
        );
        recorderOptions.mimeType = "audio/webm";
      }

      this.mediaRecorder = new MediaRecorder(this.mediaStream, {
        mimeType: recorderOptions.mimeType,
        audioBitsPerSecond: recorderOptions.audioBitsPerSecond,
      });

      // 设置事件监听器
      this.setupRecorderEvents(recorderOptions.timeslice!);

      console.log("[AudioService] Recording initialized successfully");
    } catch (error) {
      console.error("[AudioService] Failed to initialize recording:", error);
      throw error;
    }
  }

  /**
   * 开始录制
   */
  startRecording(): void {
    if (!this.mediaRecorder) {
      throw new Error(
        "Recording not initialized. Call initializeRecording() first."
      );
    }

    if (this.mediaRecorder.state === "recording") {
      console.warn("[AudioService] Already recording");
      return;
    }

    console.log("[AudioService] Starting recording");
    this.audioChunks = [];
    this.mediaRecorder.start(this.defaultRecorderOptions.timeslice);
    this.notifyRecordingState(true);
  }

  /**
   * 停止录制
   */
  stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
        reject(new Error("No active recording to stop"));
        return;
      }

      console.log("[AudioService] Stopping recording");

      const handleStop = () => {
        this.mediaRecorder!.removeEventListener("stop", handleStop);
        const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" });
        this.notifyRecordingState(false);
        resolve(audioBlob);
      };

      this.mediaRecorder.addEventListener("stop", handleStop);
      this.mediaRecorder.stop();
    });
  }

  /**
   * 暂停录制
   */
  pauseRecording(): void {
    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      console.log("[AudioService] Pausing recording");
      this.mediaRecorder.pause();
    }
  }

  /**
   * 恢复录制
   */
  resumeRecording(): void {
    if (this.mediaRecorder && this.mediaRecorder.state === "paused") {
      console.log("[AudioService] Resuming recording");
      this.mediaRecorder.resume();
    }
  }

  /**
   * 播放音频
   */
  async playAudio(
    audioData: Blob | ArrayBuffer | string,
    options?: AudioPlayerOptions
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        console.log("[AudioService] Playing audio");

        // 停止当前播放
        this.stopAudio();

        const playerOptions = { ...this.defaultPlayerOptions, ...options };
        this.currentAudio = new Audio();

        // 处理不同类型的音频数据
        let audioUrl: string;
        if (typeof audioData === "string") {
          audioUrl = audioData;
        } else if (audioData instanceof ArrayBuffer) {
          const blob = new Blob([audioData], { type: "audio/webm" });
          audioUrl = URL.createObjectURL(blob);
        } else {
          audioUrl = URL.createObjectURL(audioData);
        }

        this.currentAudio.src = audioUrl;
        this.currentAudio.volume = playerOptions.volume!;
        this.currentAudio.autoplay = playerOptions.autoplay!;

        // 设置事件监听器
        this.currentAudio.onplay = () => {
          console.log("[AudioService] Audio playback started");
          this.notifyPlaybackState(true);
        };

        this.currentAudio.onpause = () => {
          console.log("[AudioService] Audio playback paused");
          this.notifyPlaybackState(false);
        };

        this.currentAudio.onended = () => {
          console.log("[AudioService] Audio playback ended");
          this.notifyPlaybackState(false);
          // 清理URL对象
          if (audioUrl.startsWith("blob:")) {
            URL.revokeObjectURL(audioUrl);
          }
          resolve();
        };

        this.currentAudio.onerror = (error) => {
          console.error("[AudioService] Audio playback error:", error);
          this.notifyPlaybackState(false);
          reject(error);
        };

        // 开始播放
        if (playerOptions.autoplay) {
          this.currentAudio.play().catch(reject);
        }
      } catch (error) {
        console.error("[AudioService] Failed to play audio:", error);
        reject(error);
      }
    });
  }

  /**
   * 停止音频播放
   */
  stopAudio(): void {
    if (this.currentAudio) {
      console.log("[AudioService] Stopping audio playback");
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
      this.notifyPlaybackState(false);
    }
  }

  /**
   * 获取当前录制状态
   */
  getRecordingState(): string {
    return this.mediaRecorder?.state || "inactive";
  }

  /**
   * 获取当前播放状态
   */
  isPlaying(): boolean {
    return this.currentAudio ? !this.currentAudio.paused : false;
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    console.log("[AudioService] Cleaning up resources");

    // 停止录制
    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      this.mediaRecorder.stop();
    }

    // 关闭媒体流
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // 停止播放
    this.stopAudio();

    // 关闭音频上下文
    if (this.audioContext && this.audioContext.state !== "closed") {
      this.audioContext.close();
      this.audioContext = null;
    }

    // 清空回调
    this.audioChunkCallbacks = [];
    this.recordingStateCallbacks = [];
    this.playbackStateCallbacks = [];
  }

  // 回调管理

  onAudioChunk(callback: AudioChunkCallback): void {
    this.audioChunkCallbacks.push(callback);
  }

  offAudioChunk(callback: AudioChunkCallback): void {
    const index = this.audioChunkCallbacks.indexOf(callback);
    if (index > -1) {
      this.audioChunkCallbacks.splice(index, 1);
    }
  }

  onRecordingState(callback: RecordingStateCallback): void {
    this.recordingStateCallbacks.push(callback);
  }

  offRecordingState(callback: RecordingStateCallback): void {
    const index = this.recordingStateCallbacks.indexOf(callback);
    if (index > -1) {
      this.recordingStateCallbacks.splice(index, 1);
    }
  }

  onPlaybackState(callback: PlaybackStateCallback): void {
    this.playbackStateCallbacks.push(callback);
  }

  offPlaybackState(callback: PlaybackStateCallback): void {
    const index = this.playbackStateCallbacks.indexOf(callback);
    if (index > -1) {
      this.playbackStateCallbacks.splice(index, 1);
    }
  }

  // 私有方法

  private setupRecorderEvents(timeslice: number): void {
    if (!this.mediaRecorder) return;

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
        // 实时发送音频块
        this.audioChunkCallbacks.forEach((callback) => {
          try {
            callback(event.data);
          } catch (error) {
            console.error("[AudioService] Audio chunk callback error:", error);
          }
        });
      }
    };

    this.mediaRecorder.onstart = () => {
      console.log("[AudioService] MediaRecorder started");
    };

    this.mediaRecorder.onstop = () => {
      console.log("[AudioService] MediaRecorder stopped");
    };

    this.mediaRecorder.onerror = (event) => {
      console.error("[AudioService] MediaRecorder error:", event);
    };
  }

  private notifyRecordingState(isRecording: boolean): void {
    this.recordingStateCallbacks.forEach((callback) => {
      try {
        callback(isRecording);
      } catch (error) {
        console.error("[AudioService] Recording state callback error:", error);
      }
    });
  }

  private notifyPlaybackState(isPlaying: boolean): void {
    this.playbackStateCallbacks.forEach((callback) => {
      try {
        callback(isPlaying);
      } catch (error) {
        console.error("[AudioService] Playback state callback error:", error);
      }
    });
  }
}

// 创建单例实例
export const audioService = new AudioService();
