# WebM 音频转换指南

## 概述

该项目现在支持将 WebM 格式的音频文件转换为 WAV 格式，以便进行语音识别(STT)。前端可以直接发送 WebM 格式的音频数据，后端会自动进行格式转换。

## 依赖安装

### 1. Python 依赖包

更新后的`requirements.txt`已包含以下新依赖：

```txt
# 音频处理
pydub==0.25.1
numpy==1.24.3
# FFmpeg Python绑定（用于音频格式转换）
ffmpeg-python==0.2.0
aiohttp==3.9.1
```

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

### 2. 系统依赖 - FFmpeg

#### Windows 用户：

1. **下载 FFmpeg**：

   - 访问 https://ffmpeg.org/download.html
   - 下载 Windows 版本（推荐使用 full 版本）
   - 解压到任意目录，例如 `C:\ffmpeg\`

2. **添加到 PATH**：

   - 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
   - 在"系统变量"中找到"Path"，点击"编辑"
   - 添加 FFmpeg 的 bin 目录路径，例如：`C:\ffmpeg\bin`
   - 重启命令行/IDE

3. **验证安装**：
   ```bash
   ffmpeg -version
   ```

#### Linux 用户：

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# 或者使用dnf
sudo dnf install ffmpeg
```

#### macOS 用户：

```bash
# 使用Homebrew
brew install ffmpeg

# 或者使用MacPorts
sudo port install ffmpeg
```

## 功能特性

### 支持的音频格式

- **输入格式**：WebM, MP3, OGG, M4A, WAV
- **输出格式**：WAV (16kHz, 16-bit, 单声道)

### 自动格式检测

系统会自动检测音频文件的格式：

```python
from services.volcengine_stt import STTAudioUtils

# 检测音频格式
audio_format = STTAudioUtils.detect_audio_format(audio_data)
print(f"检测到的格式: {audio_format}")
```

### 格式转换

```python
# 自动转换为WAV格式
wav_data = STTAudioUtils.convert_to_wav(webm_data, "webm")
```

## 使用方法

### 1. 在 STT 服务中使用

STT 服务现在会自动处理格式转换：

```python
from services.volcengine_stt import VolcengineSTTService

# 创建STT服务实例
stt_service = VolcengineSTTService(
    access_key="your_access_key",
    app_id="your_app_id"
)

# 直接传入WebM数据，服务会自动转换
result = await stt_service.speech_to_text(webm_audio_data)
```

### 2. 前端集成

前端可以直接发送 WebM 格式：

```javascript
// 前端录音并发送WebM格式
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm',
})

mediaRecorder.ondataavailable = async (event) => {
  if (event.data.size > 0) {
    const audioBlob = event.data
    const arrayBuffer = await audioBlob.arrayBuffer()

    // 发送到后端（WebSocket或HTTP）
    websocket.send(
      JSON.stringify({
        type: 'audio_chunk',
        data: Array.from(new Uint8Array(arrayBuffer)),
      })
    )
  }
}
```

### 3. 测试转换功能

使用提供的测试脚本：

```bash
cd backend
python test_audio_conversion.py
```

## 工作流程

1. **格式检测**：系统首先检测音频数据的格式
2. **格式转换**：如果不是 WAV 格式，自动转换为 WAV
3. **标准化**：转换为 16kHz, 16-bit, 单声道 WAV 格式
4. **STT 处理**：使用转换后的 WAV 数据进行语音识别

## 日志输出

系统会记录详细的转换过程：

```
[VolcengineSTT] 检测到音频格式: webm
[VolcengineSTT] 音频格式为 webm，需要转换为WAV格式
[STTAudioUtils] 开始转换音频格式: webm -> wav
[STTAudioUtils] 转换成功，原始大小: 50432 bytes, WAV大小: 64044 bytes
[VolcengineSTT] 音频转换成功，新的数据大小: 64044 bytes
```

## 错误处理

### 常见错误及解决方案

1. **"音频处理库未安装"**

   - 确保已安装 pydub 和 ffmpeg-python
   - 检查系统是否安装 FFmpeg

2. **"ffmpeg not found"**

   - 确保 FFmpeg 已正确安装并添加到 PATH
   - 重启命令行/IDE

3. **"音频格式转换失败"**
   - 检查音频文件是否损坏
   - 确认音频格式是否支持

## 性能考虑

- **内存使用**：转换过程会创建临时文件，转换完成后自动清理
- **转换时间**：通常在几秒内完成，取决于音频文件大小
- **文件大小**：转换为 WAV 格式后，文件大小可能会增加

## 开发调试

### 保存调试文件

系统会自动保存转换后的文件用于调试：

```python
# 原始文件: audio.webm
# 转换后文件: audio.converted.wav
```

### 测试不同格式

```python
# 测试WebM转换
webm_data = open("test.webm", "rb").read()
wav_data = STTAudioUtils.convert_to_wav(webm_data, "webm")

# 测试MP3转换
mp3_data = open("test.mp3", "rb").read()
wav_data = STTAudioUtils.convert_to_wav(mp3_data, "mp3")
```

## 故障排除

如果遇到问题，请检查：

1. **依赖安装**：确保所有 Python 包都已安装
2. **FFmpeg 路径**：确保 FFmpeg 在系统 PATH 中
3. **文件权限**：确保有权限创建临时文件
4. **音频文件完整性**：确保音频文件没有损坏

有关更多问题，请查看日志输出或联系开发团队。
