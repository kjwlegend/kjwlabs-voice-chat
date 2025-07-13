"""
火山引擎语音识别(STT)服务模块
基于官方WebSocket demo实现
"""

import asyncio
import aiohttp
import json
import struct
import gzip
import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
import io
import tempfile
import os

# 音频处理库
try:
    import subprocess
    import tempfile

    # 检查FFmpeg是否可用
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode == 0:
        AUDIO_PROCESSING_AVAILABLE = True
    else:
        AUDIO_PROCESSING_AVAILABLE = False
except (ImportError, FileNotFoundError):
    AUDIO_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)

# 常量定义
DEFAULT_SAMPLE_RATE = 16000


class ProtocolVersion:
    """协议版本"""

    V1 = 0b0001


class MessageType:
    """消息类型"""

    CLIENT_FULL_REQUEST = 0b0001
    CLIENT_AUDIO_ONLY_REQUEST = 0b0010
    SERVER_FULL_RESPONSE = 0b1001
    SERVER_ERROR_RESPONSE = 0b1111


class MessageTypeSpecificFlags:
    """消息类型特定标志"""

    NO_SEQUENCE = 0b0000
    POS_SEQUENCE = 0b0001
    NEG_SEQUENCE = 0b0010
    NEG_WITH_SEQUENCE = 0b0011


class SerializationType:
    """序列化类型"""

    NO_SERIALIZATION = 0b0000
    JSON = 0b0001


class CompressionType:
    """压缩类型"""

    GZIP = 0b0001


class STTAudioUtils:
    """音频处理工具类"""

    @staticmethod
    def gzip_compress(data: bytes) -> bytes:
        """GZIP压缩数据"""
        return gzip.compress(data)

    @staticmethod
    def gzip_decompress(data: bytes) -> bytes:
        """GZIP解压缩数据"""
        return gzip.decompress(data)

    @staticmethod
    def judge_wav(data: bytes) -> bool:
        """判断是否为WAV格式"""
        if len(data) < 44:
            return False
        return data[:4] == b"RIFF" and data[8:12] == b"WAVE"

    @staticmethod
    def judge_webm(data: bytes) -> bool:
        """判断是否为WebM格式"""
        if len(data) < 4:
            return False
        # WebM文件以EBML头开始
        return data[:4] == b"\x1a\x45\xdf\xa3"

    @staticmethod
    def detect_audio_format(data: bytes) -> str:
        """检测音频格式"""
        if len(data) < 16:
            return "unknown"

        # 检查WAV格式
        if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
            return "wav"

        # 检查WebM格式
        if data[:4] == b"\x1a\x45\xdf\xa3":
            return "webm"

        # 检查MP3格式
        if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
            return "mp3"

        # 检查OGG格式
        if data[:4] == b"OggS":
            return "ogg"

        # 检查M4A格式
        if b"ftyp" in data[:20]:
            return "m4a"

        logger.warning(f"[STTAudioUtils] 未识别的音频格式，数据头部: {data[:16].hex()}")
        return "unknown"

    @staticmethod
    def convert_to_wav(data: bytes, input_format: str = "webm") -> bytes:
        """
        将音频数据转换为WAV格式 - 使用FFmpeg直接转换

        Args:
            data: 原始音频数据
            input_format: 输入格式 (webm, mp3, ogg, m4a等)

        Returns:
            bytes: 转换后的WAV数据
        """
        import subprocess
        import tempfile
        import os

        logger.info(f"[STTAudioUtils] 开始转换音频格式: {input_format} -> WAV")

        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            suffix=f".{input_format}", delete=False
        ) as temp_input:
            temp_input.write(data)
            temp_input.flush()
            input_path = temp_input.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_output:
            output_path = temp_output.name

        try:
            # 使用 FFmpeg 命令行直接转换为WAV格式
            # 根据火山引擎STT服务要求：16位PCM, 16kHz, 单声道
            cmd = [
                "ffmpeg",
                "-y",  # 覆盖输出文件
                "-i",
                input_path,  # 输入文件
                "-acodec",
                "pcm_s16le",  # 16位PCM编码
                "-ac",
                "1",  # 单声道
                "-ar",
                "16000",  # 16kHz采样率
                "-f",
                "wav",  # WAV格式
                output_path,
            ]

            logger.info(f"[STTAudioUtils] 执行FFmpeg命令: {' '.join(cmd)}")

            # 执行转换
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"[STTAudioUtils] FFmpeg转换失败: {result.stderr}")
                raise Exception(f"FFmpeg转换失败: {result.stderr}")

            # 读取转换后的WAV数据
            with open(output_path, "rb") as f:
                wav_data = f.read()

            logger.info(
                f"[STTAudioUtils] WAV转换成功，原始大小: {len(data)} bytes, WAV大小: {len(wav_data)} bytes"
            )

            return wav_data

        except subprocess.TimeoutExpired:
            logger.error("[STTAudioUtils] FFmpeg转换超时")
            raise Exception("音频转换超时")
        except Exception as e:
            logger.error(f"[STTAudioUtils] 音频转换失败: {str(e)}")
            raise Exception(f"音频格式转换失败: {str(e)}")
        finally:
            # 清理临时文件
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except:
                pass

    @staticmethod
    def extract_pcm_from_wav(wav_data: bytes) -> bytes:
        """
        从WAV文件中提取PCM数据

        Args:
            wav_data: WAV格式的音频数据

        Returns:
            bytes: 提取的PCM数据
        """
        if len(wav_data) < 44:
            raise ValueError("Invalid WAV file: too short")

        # 检查WAV头
        if wav_data[:4] != b"RIFF" or wav_data[8:12] != b"WAVE":
            raise ValueError("Invalid WAV file format")

        # 找到data chunk
        pos = 12
        while pos < len(wav_data):
            chunk_id = wav_data[pos : pos + 4]
            chunk_size = struct.unpack("<I", wav_data[pos + 4 : pos + 8])[0]

            if chunk_id == b"data":
                # 找到数据块，返回PCM数据
                pcm_data = wav_data[pos + 8 : pos + 8 + chunk_size]
                logger.info(
                    f"[STTAudioUtils] 从WAV中提取PCM数据: {len(pcm_data)} bytes"
                )
                return pcm_data

            pos += 8 + chunk_size

        raise ValueError("No data chunk found in WAV file")

    @staticmethod
    def read_wav_info(data: bytes) -> Tuple[int, int, int, int, bytes]:
        """读取WAV文件信息"""
        if len(data) < 44:
            raise ValueError("Invalid WAV file: too short")

        # 解析WAV头
        chunk_id = data[:4]
        if chunk_id != b"RIFF":
            raise ValueError("Invalid WAV file: not RIFF format")

        format_ = data[8:12]
        if format_ != b"WAVE":
            raise ValueError("Invalid WAV file: not WAVE format")

        # 解析fmt子块
        audio_format = struct.unpack("<H", data[20:22])[0]
        num_channels = struct.unpack("<H", data[22:24])[0]
        sample_rate = struct.unpack("<I", data[24:28])[0]
        bits_per_sample = struct.unpack("<H", data[34:36])[0]

        # 查找data子块
        pos = 36
        while pos < len(data) - 8:
            subchunk_id = data[pos : pos + 4]
            subchunk_size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
            if subchunk_id == b"data":
                wave_data = data[pos + 8 : pos + 8 + subchunk_size]
                return (
                    num_channels,
                    bits_per_sample // 8,
                    sample_rate,
                    subchunk_size // (num_channels * (bits_per_sample // 8)),
                    wave_data,
                )
            pos += 8 + subchunk_size

        raise ValueError("Invalid WAV file: no data subchunk found")


class STTRequestHeader:
    """STT请求头"""

    def __init__(self):
        self.message_type = MessageType.CLIENT_FULL_REQUEST
        self.message_type_specific_flags = MessageTypeSpecificFlags.POS_SEQUENCE
        self.serialization_type = SerializationType.JSON
        self.compression_type = CompressionType.GZIP
        self.reserved_data = bytes([0x00])

    def with_message_type(self, message_type: int) -> "STTRequestHeader":
        """设置消息类型"""
        self.message_type = message_type
        return self

    def with_message_type_specific_flags(self, flags: int) -> "STTRequestHeader":
        """设置消息类型特定标志"""
        self.message_type_specific_flags = flags
        return self

    def with_serialization_type(self, serialization_type: int) -> "STTRequestHeader":
        """设置序列化类型"""
        self.serialization_type = serialization_type
        return self

    def with_compression_type(self, compression_type: int) -> "STTRequestHeader":
        """设置压缩类型"""
        self.compression_type = compression_type
        return self

    def to_bytes(self) -> bytes:
        """转换为字节"""
        header = bytearray()
        header.append((ProtocolVersion.V1 << 4) | 1)
        header.append((self.message_type << 4) | self.message_type_specific_flags)
        header.append((self.serialization_type << 4) | self.compression_type)
        header.extend(self.reserved_data)
        return bytes(header)

    @staticmethod
    def default_header() -> "STTRequestHeader":
        """获取默认请求头"""
        return STTRequestHeader()


class STTRequestBuilder:
    """STT请求构建器"""

    def __init__(self, access_key: str, app_id: str):
        self.access_key = access_key
        self.app_id = app_id

    def build_auth_headers(self) -> Dict[str, str]:
        """构建认证头"""
        reqid = str(uuid.uuid4())
        return {
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Request-Id": reqid,
            "X-Api-Access-Key": self.access_key,
            "X-Api-App-Key": self.app_id,
        }

    def build_full_client_request(self, seq: int, config: Dict[str, Any]) -> bytes:
        """构建完整客户端请求"""
        header = STTRequestHeader.default_header().with_message_type_specific_flags(
            MessageTypeSpecificFlags.POS_SEQUENCE
        )

        # 直接使用传入的config字典作为payload
        payload = config

        # 序列化和压缩
        payload_bytes = json.dumps(payload).encode("utf-8")
        compressed_payload = STTAudioUtils.gzip_compress(payload_bytes)
        payload_size = len(compressed_payload)

        # 构建请求
        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack(">i", seq))
        request.extend(struct.pack(">I", payload_size))
        request.extend(compressed_payload)

        return bytes(request)

    def build_audio_only_request(
        self, seq: int, segment: bytes, is_last: bool = False
    ) -> bytes:
        """构建仅音频请求"""
        header = STTRequestHeader.default_header()
        if is_last:
            header.with_message_type_specific_flags(
                MessageTypeSpecificFlags.NEG_WITH_SEQUENCE
            )
            seq = -seq
        else:
            header.with_message_type_specific_flags(
                MessageTypeSpecificFlags.POS_SEQUENCE
            )
        header.with_message_type(MessageType.CLIENT_AUDIO_ONLY_REQUEST)

        request = bytearray()
        request.extend(header.to_bytes())
        request.extend(struct.pack(">i", seq))

        compressed_segment = STTAudioUtils.gzip_compress(segment)
        request.extend(struct.pack(">I", len(compressed_segment)))
        request.extend(compressed_segment)

        return bytes(request)


class STTResponse:
    """STT响应类"""

    def __init__(self):
        self.code = 0
        self.event = 0
        self.is_last_package = False
        self.payload_sequence = 0
        self.payload_size = 0
        self.payload_msg = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "event": self.event,
            "is_last_package": self.is_last_package,
            "payload_sequence": self.payload_sequence,
            "payload_size": self.payload_size,
            "payload_msg": self.payload_msg,
        }


class STTResponseParser:
    """STT响应解析器"""

    @staticmethod
    def parse_response(msg: bytes) -> STTResponse:
        """解析响应消息"""
        response = STTResponse()

        header_size = msg[0] & 0x0F
        message_type = msg[1] >> 4
        message_type_specific_flags = msg[1] & 0x0F
        serialization_method = msg[2] >> 4
        message_compression = msg[2] & 0x0F

        payload = msg[header_size * 4 :]

        # 解析message_type_specific_flags
        if message_type_specific_flags & 0x01:
            response.payload_sequence = struct.unpack(">i", payload[:4])[0]
            payload = payload[4:]
        if message_type_specific_flags & 0x02:
            response.is_last_package = True
        if message_type_specific_flags & 0x04:
            response.event = struct.unpack(">i", payload[:4])[0]
            payload = payload[4:]

        # 解析message_type
        if message_type == MessageType.SERVER_FULL_RESPONSE:
            response.payload_size = struct.unpack(">I", payload[:4])[0]
            payload = payload[4:]
        elif message_type == MessageType.SERVER_ERROR_RESPONSE:
            response.code = struct.unpack(">i", payload[:4])[0]
            response.payload_size = struct.unpack(">I", payload[4:8])[0]
            payload = payload[8:]

        if not payload:
            return response

        # 解压缩
        if message_compression == CompressionType.GZIP:
            try:
                payload = STTAudioUtils.gzip_decompress(payload)
            except Exception as e:
                logger.error(f"Failed to decompress payload: {e}")
                return response

        # 解析payload
        try:
            if serialization_method == SerializationType.JSON:
                response.payload_msg = json.loads(payload.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse payload: {e}")

        return response


class VolcengineSTTService:
    """火山引擎STT服务"""

    def __init__(
        self,
        access_key: str,
        app_id: str,
        segment_duration: int = 200,
        test_mode: bool = False,
    ):
        """
        初始化STT服务

        Args:
            access_key: 访问密钥
            app_id: 应用ID
            segment_duration: 音频分段时长(ms)
            test_mode: 是否启用测试模式
        """
        self.access_key = access_key
        self.app_id = app_id
        self.segment_duration = segment_duration
        self.test_mode = test_mode
        self.request_builder = STTRequestBuilder(access_key, app_id)

        # 默认WebSocket URL (根据官方demo)
        self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"

        # 默认STT配置 - 根据官方demo修正
        self.default_config = {
            "user": {"uid": "demo_uid"},
            "audio": {
                "format": "wav",  # 使用WAV格式，不是s16le
                "codec": "raw",  # 原始编码
                "rate": 16000,  # 16kHz采样率
                "bits": 16,  # 16位
                "channel": 1,  # 单声道
            },
            "request": {
                "model_name": "bigmodel",
                "enable_itn": True,
                "enable_punc": True,
                "enable_ddc": True,
                "show_utterances": True,
                "enable_nonstream": False,
            },
        }

        logger.info(f"[VolcengineSTT] 初始化完成 - App ID: {app_id}")
        logger.info(f"[VolcengineSTT] 🎤 WebSocket URL: {self.ws_url}")

    def _calculate_segment_size(self, wav_data: bytes) -> int:
        """
        计算WAV音频分段大小

        Args:
            wav_data: WAV音频数据

        Returns:
            int: 分段大小（字节）
        """
        try:
            # 使用WAV信息计算分段大小
            channel_num, samp_width, frame_rate, _, _ = STTAudioUtils.read_wav_info(
                wav_data
            )[:5]
            size_per_sec = channel_num * samp_width * frame_rate
            segment_size = size_per_sec * self.segment_duration // 1000

            logger.info(
                f"[VolcengineSTT] 计算分段大小: {segment_size} bytes ({self.segment_duration}ms)"
            )
            return segment_size
        except Exception as e:
            logger.error(f"[VolcengineSTT] 计算分段大小失败: {e}")
            # 返回默认分段大小 (16000Hz * 2bytes * 1channel * 0.2s)
            return 16000 * 2 * 1 * self.segment_duration // 1000

    def _split_audio(self, wav_data: bytes, segment_size: int) -> List[bytes]:
        """
        分割WAV音频数据 - 根据官方demo实现

        Args:
            wav_data: WAV音频数据
            segment_size: 分段大小

        Returns:
            List[bytes]: 分割后的音频段列表
        """
        if segment_size <= 0:
            return []

        segments = []

        # 根据官方demo：直接分割整个WAV数据，不跳过头部
        for i in range(0, len(wav_data), segment_size):
            end = min(i + segment_size, len(wav_data))
            segment = wav_data[i:end]
            segments.append(segment)

        logger.info(
            f"[VolcengineSTT] 分割WAV数据: {len(segments)} 个段，每段约 {segment_size} bytes"
        )
        return segments

    def _extract_text_from_result(self, result: Dict[str, Any]) -> str:
        """
        从单个STT结果中提取文本内容

        Args:
            result: 火山引擎STT返回的单个结果

        Returns:
            str: 提取的文本内容，如果没有文本则返回空字符串
        """
        try:
            if not isinstance(result, dict):
                return ""

            # 检查是否有result字段
            if "result" not in result:
                return ""

            result_data = result["result"]

            # 方式1: 直接的text字段
            if "text" in result_data and result_data["text"]:
                text = result_data["text"].strip()
                logger.debug(f"[VolcengineSTT] 从text字段提取: '{text}'")
                return text

            # 方式2: utterances数组（多段识别结果）
            if "utterances" in result_data:
                texts = []
                for utterance in result_data["utterances"]:
                    if "text" in utterance and utterance["text"]:
                        texts.append(utterance["text"].strip())
                if texts:
                    text = " ".join(texts)
                    logger.debug(f"[VolcengineSTT] 从utterances提取: '{text}'")
                    return text

            # 方式3: segments数组（分段识别结果）
            if "segments" in result_data:
                texts = []
                for segment in result_data["segments"]:
                    if "text" in segment and segment["text"]:
                        texts.append(segment["text"].strip())
                if texts:
                    text = " ".join(texts)
                    logger.debug(f"[VolcengineSTT] 从segments提取: '{text}'")
                    return text

            # 方式4: 检查是否有words数组
            if "words" in result_data:
                texts = []
                for word in result_data["words"]:
                    if "text" in word and word["text"]:
                        texts.append(word["text"].strip())
                if texts:
                    text = " ".join(texts)
                    logger.debug(f"[VolcengineSTT] 从words提取: '{text}'")
                    return text

            logger.debug(
                f"[VolcengineSTT] 结果中没有找到可用的文本字段: {result_data.keys()}"
            )
            return ""

        except Exception as e:
            logger.error(f"[VolcengineSTT] 提取文本时出错: {e}")
            return ""

    async def speech_to_text(self, audio_data: bytes, **kwargs) -> str:
        """
        语音转文本

        Args:
            audio_data: 音频数据
            **kwargs: 其他参数

        Returns:
            str: 识别的文本
        """
        logger.info(f"[VolcengineSTT] 开始语音识别，音频大小: {len(audio_data)} bytes")

        # 测试模式：返回模拟结果
        if self.test_mode:
            logger.info("[VolcengineSTT] 测试模式：返回模拟识别结果")
            if len(audio_data) < 100:
                return "音频数据不足"
            return f"这是语音识别的模拟结果，音频大小: {len(audio_data)} bytes"

        try:
            # 创建配置
            config = {**self.default_config, **kwargs}

            # 检测音频格式并转换为WAV
            audio_format = STTAudioUtils.detect_audio_format(audio_data)
            logger.info(f"[VolcengineSTT] 检测到音频格式: {audio_format}")

            # 确保音频是WAV格式
            if audio_format != "wav":
                logger.info(f"[VolcengineSTT] 音频格式为 {audio_format}，转换为WAV格式")

                if not AUDIO_PROCESSING_AVAILABLE:
                    logger.error("[VolcengineSTT] 音频处理库未安装，无法转换音频格式")
                    raise Exception(
                        "音频处理库未安装，无法转换音频格式。请确保安装了 ffmpeg"
                    )

                try:
                    # 转换为WAV格式
                    wav_data = STTAudioUtils.convert_to_wav(audio_data, audio_format)
                    logger.info(
                        f"[VolcengineSTT] 音频转换成功，WAV数据大小: {len(wav_data)} bytes"
                    )
                except Exception as e:
                    logger.error(f"[VolcengineSTT] 音频转换失败: {str(e)}")
                    raise Exception(f"音频格式转换失败: {str(e)}")
            else:
                logger.info("[VolcengineSTT] 音频已是WAV格式，无需转换")
                wav_data = audio_data

            # 验证WAV格式
            if not STTAudioUtils.judge_wav(wav_data):
                logger.warning("[VolcengineSTT] 音频数据不是有效的WAV格式")
                raise Exception("音频数据不是有效的WAV格式")

            # 使用WebSocket进行识别
            async with aiohttp.ClientSession() as session:
                seq = 1
                headers = self.request_builder.build_auth_headers()

                logger.info(f"[VolcengineSTT] 连接WebSocket: {self.ws_url}")

                async with session.ws_connect(self.ws_url, headers=headers) as ws:
                    logger.info("[VolcengineSTT] WebSocket连接成功")

                    # 发送初始请求
                    initial_request = self.request_builder.build_full_client_request(
                        seq, config
                    )
                    await ws.send_bytes(initial_request)
                    logger.info(f"[VolcengineSTT] 发送初始请求，序列号: {seq}")

                    # 接收初始响应
                    msg = await ws.receive()
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        initial_response = STTResponseParser.parse_response(msg.data)
                        logger.info(
                            f"[VolcengineSTT] 收到初始响应: {initial_response.to_dict()}"
                        )

                        if initial_response.code != 0:
                            raise Exception(
                                f"STT初始化失败: {initial_response.payload_msg}"
                            )

                    seq += 1

                    # 计算分段大小
                    segment_size = self._calculate_segment_size(wav_data)

                    # 分割WAV音频
                    wav_segments = self._split_audio(wav_data, segment_size)
                    total_segments = len(wav_segments)
                    logger.info(f"[VolcengineSTT] 分割为 {total_segments} 个WAV音频段")

                    # 发送WAV音频段
                    for i, segment in enumerate(wav_segments):
                        is_last = i == total_segments - 1
                        audio_request = self.request_builder.build_audio_only_request(
                            seq, segment, is_last=is_last
                        )
                        await ws.send_bytes(audio_request)
                        logger.info(
                            f"[VolcengineSTT] 发送WAV音频段 {i+1}/{total_segments}，序列号: {seq}，大小: {len(segment)} bytes，最后一段: {is_last}"
                        )

                        if not is_last:
                            seq += 1

                    # 接收所有响应
                    results = []
                    while True:
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            response = STTResponseParser.parse_response(msg.data)
                            logger.info(
                                f"[VolcengineSTT] 收到响应: {response.to_dict()}"
                            )

                            if response.code != 0:
                                logger.error(
                                    f"[VolcengineSTT] 识别错误: {response.payload_msg}"
                                )
                                break

                            if response.payload_msg:
                                results.append(response.payload_msg)
                                # 调试：打印每个流式结果
                                extracted_text = self._extract_text_from_result(
                                    response.payload_msg
                                )
                                if extracted_text:
                                    logger.info(
                                        f"[VolcengineSTT] 流式结果 #{len(results)}: '{extracted_text}'"
                                    )

                            if response.is_last_package:
                                logger.info("[VolcengineSTT] 收到最后一个响应包")
                                break

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"[VolcengineSTT] WebSocket错误: {msg.data}")
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.info("[VolcengineSTT] WebSocket连接关闭")
                            break

                    # 处理结果 - 修正流式识别重复问题
                    if results:
                        # 只取最后一个结果（最完整的识别结果）
                        last_result = results[-1]
                        final_text = self._extract_text_from_result(last_result)

                        if final_text:
                            logger.info(f"[VolcengineSTT] 最终识别结果: {final_text}")
                            logger.info(
                                f"[VolcengineSTT] 共收到 {len(results)} 个流式结果，使用最后一个"
                            )
                            return final_text
                        else:
                            logger.warning(
                                "[VolcengineSTT] 最后一个结果中没有找到文本内容"
                            )
                            return "无法识别音频内容"
                    else:
                        logger.warning("[VolcengineSTT] 没有收到有效的识别结果")
                        return "无法识别音频内容"

        except Exception as e:
            logger.error(f"[VolcengineSTT] 语音识别异常: {str(e)}")
            raise Exception(f"语音识别失败: {str(e)}")

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接状态"""
        try:
            logger.info("[VolcengineSTT] 测试连接...")

            # 创建1秒的WAV测试数据
            sample_rate = 16000
            duration_seconds = 1
            channels = 1
            bits_per_sample = 16

            # 计算音频数据大小
            samples_per_second = sample_rate * channels
            bytes_per_sample = bits_per_sample // 8
            audio_data_size = samples_per_second * bytes_per_sample * duration_seconds

            # 生成静音PCM数据
            pcm_data = b"\x00\x00" * (audio_data_size // 2)

            # 创建正确的WAV文件头
            file_size = 36 + len(pcm_data)  # 44字节头部 - 8字节 + 音频数据

            wav_header = (
                b"RIFF"
                + struct.pack("<I", file_size)  # 文件大小-8
                + b"WAVE"
                + b"fmt "
                + struct.pack("<I", 16)  # fmt chunk大小
                + struct.pack("<H", 1)  # 音频格式 PCM
                + struct.pack("<H", channels)  # 通道数
                + struct.pack("<I", sample_rate)  # 采样率
                + struct.pack("<I", sample_rate * channels * bytes_per_sample)  # 字节率
                + struct.pack("<H", channels * bytes_per_sample)  # 块对齐
                + struct.pack("<H", bits_per_sample)  # 位深度
                + b"data"
                + struct.pack("<I", len(pcm_data))  # data chunk大小
            )

            # 组合完整的WAV文件
            test_wav_data = wav_header + pcm_data

            logger.info(f"[VolcengineSTT] 生成测试WAV数据: {len(test_wav_data)} bytes")

            # 尝试转换文本
            test_text = await self.speech_to_text(test_wav_data)

            return {
                "status": "success",
                "message": "STT服务连接正常",
                "test_result": test_text,
                "wav_data_size": len(test_wav_data),
            }

        except Exception as e:
            logger.error(f"[VolcengineSTT] 连接测试失败: {str(e)}")
            return {
                "status": "error",
                "message": f"STT服务连接失败: {str(e)}",
                "error_details": str(e),
            }
