# nonebot-plugin-xisoul

[![License](https://img.shields.io/github/license/xisoul/nonebot-plugin-xisoul)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![NoneBot Version](https://img.shields.io/badge/nonebot-2.0.0+-green.svg)](https://github.com/nonebot/nonebot2)

NoneBot 插件：提供农历黄历信息、实时新闻图片、随机图片、AI 聊天以及 AI 绘图功能

## 功能介绍

- 📅 获取当天农历黄历信息（文本版和图片版）
- 📰 获取实时热榜新闻图片
- 🖼️ 随机图片功能（支持多种类型图片获取）
- 🤖 AI 聊天功能（支持 OpenAI 兼容 API）
  - 群聊：@机器人 触发
  - 私聊：直接对话
  - 支持图片分析（模型支持时）
  - 支持引用消息
  - SQLite 会话持久化
  - 斜杠指令：/help、/new、/clear、/model、/models
- ⏰ 支持定时发送新闻图片到指定群聊
- 💾 支持本地缓存，避免频繁调用API
- 🎨 AI 绘图功能（基于独立的绘图 API，支持自定义模型）

## 安装

```bash
# 使用 nb-cli 安装
nb plugin install nonebot-plugin-xisoul

# 或使用 pip 安装
pip install nonebot-plugin-xisoul
```

## 依赖说明

### 核心依赖（自动安装）
- `nonebot2>=2.0.0` - 插件基础框架
- `nonebot-adapter-onebot>=2.3.0` - OneBot协议适配器
- `nonebot-plugin-apscheduler>=0.1.2` - 定时任务支持
- `httpx>=0.23.0` - HTTP请求客户端

### 可选依赖（需要手动安装）
- **网页渲染依赖**：`nonebot-plugin-htmlrender` - 用于生成黄历图片（可通过 `nb plugin install nonebot-plugin-htmlrender` 安装）
- **SOCKS代理支持**：`httpx[socks]` - 如果实例启用了 SOCKS4/SOCKS5 代理，建议额外安装 `pip install "httpx[socks]"`

## 配置项

默认先读取 `.env`，如果 `.env` 中设置了 `ENVIRONMENT=prod` 且存在 `.env.prod`，则会继续读取 `.env.prod`。

建议：
- 基础环境选择放在 `.env`
- 实际业务配置放在 `.env.prod`

例如：

```env
# .env
ENVIRONMENT=prod
```

然后在 `.env.prod` 文件中添加以下配置：

```env
# 黄历API配置
LUNAR_CALENDAR_API_KEY="您的API密钥"

# 新闻API配置
SHWGIJ_API_KEY="您的新闻API密钥"

# 定时任务配置
# 格式: 分 时 日 月 周
SHWGIJ_CRON_EXPRESSION="0 8 * * *"
# 定时任务发送的群聊ID列表，多个群ID用逗号分隔
SHWGIJ_SEND_GROUPS="群聊ID1,群聊ID2"
# 是否启用定时任务，1-启用，0-禁用
SHWGIJ_CRON_ENABLE=1

# AI 聊天配置（OpenAI 兼容 API）
OPENAI_BASE_URL="https://api.openai.com/v1"  # API 地址
OPENAI_API_KEY="您的 API 密钥"
OPENAI_MODEL="gpt-4o-mini"  # 默认模型
OPENAI_MODELS="gpt-4o-mini,gpt-4,claude-3-opus"  # 可用模型列表（逗号分隔）
AI_CHAT_DB_PATH="./ai_chat.db"  # SQLite 数据库路径（可选）
AI_CHAT_MAX_TURNS=20  # 上下文对话轮数（可选，默认20）
AI_CHAT_TIMEOUT=120  # HTTP 请求超时秒数（可选，默认120）

# 日志级别配置 (可选：DEBUG, INFO, WARNING, ERROR)
SHWGIJ_LOG_LEVEL="INFO"
# 图片删除延时时间（秒）
SHWGIJ_IMAGE_DELETE_DELAY=120
# 缓存文件保留天数
SHWGIJ_CACHE_EXPIRE_DAYS=7

# 绘图 API 独立配置（与 AI 聊天分开，使用独立的接口和模型）
IMAGE_GEN_BASE_URL="https://你的绘图API地址/v1"  # 绘图 API 地址
IMAGE_GEN_API_KEY="你的绘图API密钥"  # 绘图 API Key
IMAGE_GEN_MODEL="你的绘图模型名"  # 绘图模型（如 dall-e-3、flux、gpt-image-1 等）
```

## 使用说明

### 黄历功能
- 文本版黄历：发送 `文字黄历` 或 `文本黄历`（无需 `/` 前缀）
- 图片版黄历：发送 `hl`（无需 `/` 前缀）
- 命令格式：`/hl` 仍然可用

### 新闻功能
- 热榜新闻图片：发送 `/新闻图片` 获取今日热榜新闻图片

### 随机图片功能
- 随机白丝图片：发送 `sjbs` 或 `/sjbs`，支持数字后缀指定数量（如 `sjbs10`）
- 随机黑丝图片：发送 `sjhs` 或 `/sjhs`
- 随机美图：发送 `sjmt` 或 `/sjmt`
- 二次元图片：发送 `sjecy` 或 `/sjecy`
- 4K美女高清图片：发送 `sjsk` 或 `/sjsk`

### AI 聊天功能

#### 群聊使用
- 直接 @机器人 + 内容进行对话
- 支持引用消息：引用别人的消息后 @机器人，机器人会读取引用的内容
- 支持图片：发送图片或引用包含图片的消息（模型支持时）

#### 私聊使用
- 直接发送消息即可对话

#### 斜杠指令
- `/help` - 显示帮助信息
- `/new` 或 `/clear` - 清空当前会话历史
- `/model <模型名>` - 切换模型（如 `/model gpt-4o-mini`）
- `/models` - 显示可用模型列表

#### 示例
```
# 群聊
@机器人 你好

# 私聊
你好

# 引用消息后 @机器人
[引用别人的问题] @机器人

# 切换模型
/model gpt-4o-mini

# 查看可用模型
/models
```

### 帮助功能
- 获取所有命令帮助：发送 `帮助`、`插件帮助` 或 `xihelp`（无需 `/` 前缀），或使用 `/帮助`、`/插件帮助`、`/xihelp`

### AI 绘图功能
- 生图：发送 `生图 提示词`（如 `生图 女孩 霓虹灯`）
- 支持格式：`生图`、`生成图片`、`画图`、`生成图`
- 支持冒号分隔：`生图: 女孩 霓虹灯` 或 `生图：女孩 霓虹灯`
- 斜杠命令：`/生图 女孩 霓虹灯`

> ⚠️ 绘图使用独立的 API 配置（`IMAGE_GEN_BASE_URL`、`IMAGE_GEN_API_KEY`、`IMAGE_GEN_MODEL`），与 AI 聊天的 `OPENAI_*` 配置互不影响。

## 许可证

本项目使用 [MIT](LICENSE) 许可证

## 致谢

感谢所有为本项目做出贡献的开发者！
