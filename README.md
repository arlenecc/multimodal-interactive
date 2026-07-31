# 多模态模型调试工具 (Multimodal Model Debugger)

基于 PyQt6 构建的多模态大模型调试工具，兼容 OpenAI 标准服务接口。支持文字、图片、音频、视频等多模态内容的发送与接收，提供实时流式输出、推理速度监控和详细的 API 通讯日志。

## 功能特性

### 配置管理
- 支持自定义 **Base URL**，兼容任意 OpenAI 接口兼容的服务（OpenAI、Azure、本地部署等）
- **API Key** 密码输入框，安全保密
- 点击「获取模型」按钮自动拉取可用模型列表，支持手动编辑
- 可调参数：**Max Tokens**、**Temperature**、**Stream** 开关
- 配置自动持久化到 `~/.multimodal_debugger_config.json`

### 多模态对话
- 支持发送 **纯文字**、**文字 + 媒体**、**纯媒体** 等多种组合
- 支持的媒体格式：
  - 图片：PNG、JPG、JPEG、GIF、WebP、BMP
  - 音频：MP3、WAV、OGG、FLAC、M4A
  - 视频：MP4、MOV、AVI、MKV、WebM
- 消息气泡式展示，自动滚动到最新消息
- 图片自动缩略图预览，音频/视频以图标展示

### 实时推理监控
- 流式输出模式下实时显示推理文本
- 实时计算并显示 **推理速度**（tokens/s）、已用时间、Token 数量
- 对话面板底部状态栏展示

### 交互日志（Debug 面板）
- 深色终端风格的日志面板，等宽字体显示
- 完整记录 HTTP **请求**（URL、Headers、Body）和 **响应**（Status、Response Body）
- 带时间戳和颜色区分（蓝色=请求，绿色=响应，红色=错误，黄色=信息）
- 支持自动滚动开关和一键清除

## 界面布局

```
┌──────────────────────────────────────────────────────────────┐
│  Base URL │ API Key │ Model [获取模型] │ Max Tokens │ Temp │  │  ← 配置面板 (1/6)
├──────────────────────────────────┬───────────────────────────┤
│                                  │                           │
│   多模态对话区域                  │    交互日志               │
│   - 消息气泡展示                 │    - HTTP 请求详情         │
│   - 图片/音频/视频预览           │    - HTTP 响应详情         │
│   - 推理速度实时显示             │    - 错误信息              │
│   - 附件预览与移除               │    - 带时间戳和颜色        │
│                                  │                           │
│   [📎] [输入消息...] [发送]      │    [清除] [自动滚动]      │
│   [清空对话]                     │                           │
│                                  │                           │
│          对话面板 (2/3)          │      日志面板 (1/3)       │
└──────────────────────────────────┴───────────────────────────┘
```

## 项目结构

```
multimodal-interactive/
├── pyproject.toml              # pytest 配置
├── requirements.txt            # Python 依赖
├── src/
│   ├── main.py                 # 应用入口
│   ├── config.py               # 配置管理 (AppConfig)
│   ├── api_client.py           # OpenAI 兼容 API 客户端
│   ├── models/
│   │   └── message.py          # 消息数据模型 (Message, MediaContent, Conversation)
│   ├── ui/
│   │   ├── main_window.py      # 主窗口 & API 工作线程
│   │   ├── config_panel.py     # 配置面板
│   │   ├── chat_panel.py       # 多模态对话面板
│   │   └── log_panel.py        # 交互日志面板
│   └── utils/
│       └── media_utils.py      # 多媒体工具函数
└── tests/
    ├── test_config.py           # 配置模块测试 (13 个)
    ├── test_message.py          # 消息模型测试 (22 个)
    ├── test_api_client.py       # API 客户端测试 (13 个)
    └── test_media_utils.py      # 媒体工具测试 (32 个)
```

## 快速开始

### 环境要求

- Python 3.10+
- macOS / Linux / Windows

### 安装

```bash
# 克隆或进入项目目录
cd multimodal-interactive

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python3 src/main.py
```

### 使用步骤

1. **配置服务地址**：在顶部 Base URL 栏填入 API 地址（如 `https://api.openai.com/v1`）
2. **填入 API Key**：输入你的 API 密钥
3. **获取模型**：点击「获取模型」按钮，从下拉列表中选择模型（也可手动输入）
4. **发送消息**：在底部输入框输入文字，点击「发送」或按 Enter 发送
5. **附加媒体**：点击 📎 按钮选择图片/音频/视频文件，可与文字一起发送
6. **查看日志**：右侧日志面板查看详细的 API 通讯过程

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift + Enter` | 输入换行 |

## 运行测试

```bash
# 运行全部测试
python3 -m pytest tests/ -v

# 运行指定模块测试
python3 -m pytest tests/test_config.py -v
python3 -m pytest tests/test_api_client.py -v
```

当前共 **80 个测试用例**，覆盖配置管理、消息模型、API 客户端和多媒体工具。

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI 框架 | PyQt6 |
| HTTP 客户端 | httpx (异步) |
| API 协议 | OpenAI Chat Completions API |
| 测试框架 | pytest + pytest-asyncio |
| 流式传输 | SSE (Server-Sent Events) |

## 兼容性

本工具兼容所有遵循 OpenAI API 规范的服务，包括但不限于：

- OpenAI (GPT-4o, GPT-4-Vision 等)
- Azure OpenAI
- 各类开源模型的 OpenAI 兼容部署（vLLM、Ollama、LocalAI 等）
- 其他支持 OpenAI `/v1/models` 和 `/v1/chat/completions` 接口的服务
