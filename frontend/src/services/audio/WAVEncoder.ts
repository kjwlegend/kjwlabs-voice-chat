/**
 * WAV文件编码器
 * 负责将PCM数据编码为WAV格式
 */
export class WAVEncoder {
  private sampleRate: number
  private numChannels: number
  private bitDepth: number

  constructor(
    sampleRate: number = 16000,
    numChannels: number = 1,
    bitDepth: number = 16
  ) {
    this.sampleRate = sampleRate
    this.numChannels = numChannels
    this.bitDepth = bitDepth
  }

  /**
   * 将Float32Array PCM数据编码为WAV格式
   */
  encodeWAV(pcmData: Float32Array): ArrayBuffer {
    const length = pcmData.length
    const bytesPerSample = this.bitDepth / 8
    const blockAlign = this.numChannels * bytesPerSample
    const byteRate = this.sampleRate * blockAlign
    const dataSize = length * bytesPerSample
    const fileSize = 36 + dataSize

    const buffer = new ArrayBuffer(44 + dataSize)
    const view = new DataView(buffer)

    // WAV头部
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, fileSize, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true) // fmt chunk size
    view.setUint16(20, 1, true) // audio format (PCM)
    view.setUint16(22, this.numChannels, true)
    view.setUint32(24, this.sampleRate, true)
    view.setUint32(28, byteRate, true)
    view.setUint16(32, blockAlign, true)
    view.setUint16(34, this.bitDepth, true)
    writeString(36, 'data')
    view.setUint32(40, dataSize, true)

    // PCM数据转换为16位整数
    let offset = 44
    for (let i = 0; i < length; i++) {
      const sample = Math.max(-1, Math.min(1, pcmData[i]))
      view.setInt16(
        offset,
        sample < 0 ? sample * 0x8000 : sample * 0x7fff,
        true
      )
      offset += 2
    }

    return buffer
  }

  /**
   * 验证PCM数据中是否包含有效音频（非静音）
   */
  hasAudioContent(pcmData: Float32Array, threshold: number = 0.001): boolean {
    return Array.from(pcmData).some((sample) => Math.abs(sample) > threshold)
  }

  /**
   * 获取PCM数据的统计信息
   */
  getAudioStats(pcmData: Float32Array): {
    maxAmplitude: number
    minAmplitude: number
    rmsAmplitude: number
    hasContent: boolean
  } {
    let max = 0
    let min = 0
    let sumSquares = 0

    for (let i = 0; i < pcmData.length; i++) {
      const sample = pcmData[i]
      max = Math.max(max, sample)
      min = Math.min(min, sample)
      sumSquares += sample * sample
    }

    const rms = Math.sqrt(sumSquares / pcmData.length)

    return {
      maxAmplitude: max,
      minAmplitude: min,
      rmsAmplitude: rms,
      hasContent: this.hasAudioContent(pcmData),
    }
  }
}
