/**
 * 格式化工具函数
 */

/**
 * 格式化时间戳为可读时间
 */
export function formatTimestamp(
  timestamp: number,
  format: "full" | "time" | "date" = "full"
): string {
  const date = new Date(timestamp);

  switch (format) {
    case "time":
      return date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    case "date":
      return date.toLocaleDateString("zh-CN");
    case "full":
    default:
      return date.toLocaleString("zh-CN");
  }
}

/**
 * 格式化时长（毫秒转为可读格式）
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}:${(minutes % 60).toString().padStart(2, "0")}:${(
      seconds % 60
    )
      .toString()
      .padStart(2, "0")}`;
  } else if (minutes > 0) {
    return `${minutes}:${(seconds % 60).toString().padStart(2, "0")}`;
  } else {
    return `${seconds}s`;
  }
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

/**
 * 格式化延迟时间
 */
export function formatLatency(ms: number): string {
  if (ms < 100) {
    return `${ms.toFixed(0)}ms`;
  } else if (ms < 1000) {
    return `${ms.toFixed(0)}ms`;
  } else {
    return `${(ms / 1000).toFixed(1)}s`;
  }
}

/**
 * 格式化百分比
 */
export function formatPercentage(
  value: number,
  total: number,
  decimals: number = 1
): string {
  if (total === 0) return "0%";
  return `${((value / total) * 100).toFixed(decimals)}%`;
}

/**
 * 格式化状态显示文本
 */
export function formatConversationState(state: string): string {
  const stateMap: Record<string, string> = {
    idle: "准备就绪",
    connecting: "连接中",
    listening: "正在聆听",
    thinking: "正在思考",
    speaking: "正在说话",
    error: "出现错误",
    disconnected: "连接断开",
  };

  return stateMap[state] || state;
}

/**
 * 格式化错误代码
 */
export function formatErrorCode(code: string): string {
  const codeMap: Record<string, string> = {
    NETWORK_ERROR: "网络错误",
    PERMISSION_DENIED: "权限被拒绝",
    DEVICE_NOT_FOUND: "设备未找到",
    API_ERROR: "API调用失败",
    TIMEOUT: "请求超时",
    INVALID_FORMAT: "格式无效",
    QUOTA_EXCEEDED: "配额超限",
  };

  return codeMap[code] || `错误代码: ${code}`;
}

/**
 * 截断长文本
 */
export function truncateText(
  text: string,
  maxLength: number = 100,
  ellipsis: string = "..."
): string {
  if (text.length <= maxLength) {
    return text;
  }

  return text.slice(0, maxLength - ellipsis.length) + ellipsis;
}

/**
 * 格式化用户输入（清理和标准化）
 */
export function formatUserInput(input: string): string {
  return input
    .trim() // 去除首尾空格
    .replace(/\s+/g, " ") // 多个空格合并为一个
    .replace(
      /[^\w\s\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3040-\u309f\u30a0-\u30ff]/g,
      ""
    ) // 保留中英文、数字、空格
    .slice(0, 1000); // 限制长度
}

/**
 * 高亮关键词
 */
export function highlightKeywords(text: string, keywords: string[]): string {
  if (!keywords.length) return text;

  const regex = new RegExp(`(${keywords.join("|")})`, "gi");
  return text.replace(regex, "<mark>$1</mark>");
}

/**
 * 格式化对话历史为可导出的文本
 */
export function formatConversationHistory(history: any[]): string {
  const lines: string[] = [];

  lines.push("# EchoFlow 对话记录");
  lines.push(`导出时间: ${formatTimestamp(Date.now())}`);
  lines.push("");

  history.forEach((turn, index) => {
    lines.push(`## 第 ${index + 1} 轮对话`);
    lines.push(`时间: ${formatTimestamp(turn.timestamp)}`);
    lines.push(`时长: ${formatDuration(turn.duration)}`);
    lines.push("");
    lines.push(`**用户:** ${turn.userInput}`);
    lines.push(`**AI:** ${turn.aiResponse}`);

    if (turn.toolCalls && turn.toolCalls.length > 0) {
      lines.push("");
      lines.push("**工具调用:**");
      turn.toolCalls.forEach((tool: any) => {
        lines.push(`- ${tool.name}: ${JSON.stringify(tool.parameters)}`);
      });
    }

    lines.push("");
    lines.push("---");
    lines.push("");
  });

  return lines.join("\n");
}
