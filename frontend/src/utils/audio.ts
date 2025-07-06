/**
 * 音频处理工具函数
 */

/**
 * 将ArrayBuffer转换为Blob
 */
export function arrayBufferToBlob(
  buffer: ArrayBuffer,
  mimeType: string = "audio/webm"
): Blob {
  return new Blob([buffer], { type: mimeType });
}

/**
 * 将Blob转换为ArrayBuffer
 */
export function blobToArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

/**
 * 将音频文件转换为Base64
 */
export function audioToBase64(audioData: Blob | ArrayBuffer): Promise<string> {
  return new Promise((resolve, reject) => {
    const blob =
      audioData instanceof ArrayBuffer
        ? arrayBufferToBlob(audioData)
        : audioData;

    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // 移除data:audio/webm;base64,前缀
      const base64 = result.split(",")[1];
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

/**
 * 从Base64创建音频Blob
 */
export function base64ToAudioBlob(
  base64: string,
  mimeType: string = "audio/webm"
): Blob {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);

  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }

  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

/**
 * 合并多个音频Blob
 */
export function mergeAudioBlobs(
  blobs: Blob[],
  mimeType: string = "audio/webm"
): Blob {
  return new Blob(blobs, { type: mimeType });
}

/**
 * 获取音频文件时长（估算）
 */
export function getAudioDuration(audioBlob: Blob): Promise<number> {
  return new Promise((resolve, reject) => {
    const audio = new Audio();
    const url = URL.createObjectURL(audioBlob);

    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(audio.duration);
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to load audio"));
    };

    audio.src = url;
  });
}

/**
 * 压缩音频文件
 */
export async function compressAudio(
  audioBlob: Blob,
  quality: number = 0.7
): Promise<Blob> {
  // 这里可以实现音频压缩逻辑
  // 简单实现：如果文件大小超过阈值，降低质量
  const maxSize = 1024 * 1024; // 1MB

  if (audioBlob.size <= maxSize) {
    return audioBlob;
  }

  // 这里可以集成音频压缩库或者Web Audio API
  // 目前返回原始文件
  console.warn("[AudioUtils] Audio compression not implemented");
  return audioBlob;
}

/**
 * 音频格式检测
 */
export function detectAudioFormat(blob: Blob): string {
  const type = blob.type;

  if (type.includes("webm")) return "webm";
  if (type.includes("mp4")) return "mp4";
  if (type.includes("ogg")) return "ogg";
  if (type.includes("wav")) return "wav";
  if (type.includes("mp3")) return "mp3";

  return "unknown";
}

/**
 * 检查浏览器音频编码支持
 */
export function checkAudioCodecSupport(): {
  webm: boolean;
  mp4: boolean;
  ogg: boolean;
  wav: boolean;
} {
  const audio = new Audio();

  return {
    webm: audio.canPlayType('audio/webm; codecs="opus"') !== "",
    mp4: audio.canPlayType('audio/mp4; codecs="mp4a.40.2"') !== "",
    ogg: audio.canPlayType('audio/ogg; codecs="vorbis"') !== "",
    wav: audio.canPlayType("audio/wav") !== "",
  };
}

/**
 * 音频流可视化数据
 */
export function getAudioVisualizationData(
  mediaStream: MediaStream,
  fftSize: number = 256
): {
  analyser: AnalyserNode;
  dataArray: Uint8Array;
  getFrequencyData: () => Uint8Array;
  getTimeDomainData: () => Uint8Array;
} {
  const audioContext = new (window.AudioContext ||
    (window as any).webkitAudioContext)();
  const analyser = audioContext.createAnalyser();
  const source = audioContext.createMediaStreamSource(mediaStream);

  analyser.fftSize = fftSize;
  source.connect(analyser);

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  return {
    analyser,
    dataArray,
    getFrequencyData: () => {
      analyser.getByteFrequencyData(dataArray);
      return dataArray;
    },
    getTimeDomainData: () => {
      analyser.getByteTimeDomainData(dataArray);
      return dataArray;
    },
  };
}

/**
 * 音频文件下载
 */
export function downloadAudio(
  audioBlob: Blob,
  filename: string = "recording.webm"
): void {
  const url = URL.createObjectURL(audioBlob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
