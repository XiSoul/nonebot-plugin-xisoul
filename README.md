# nonebot-plugin-xisoul

[![License](https://img.shields.io/github/license/xisoul/nonebot-plugin-xisoul)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![NoneBot Version](https://img.shields.io/badge/nonebot-2.0.0+-green.svg)](https://github.com/nonebot/nonebot2)

NoneBot 插件：提供农历黄历信息和实时新闻图片功能，以及Ollama对话功能

## 功能介绍

- 📅 获取当天农历黄历信息（文本版和图片版）
- 📰 获取实时热榜新闻图片
- ⏰ 支持定时发送新闻图片到指定群聊
- 💾 支持本地缓存，避免频繁调用API
- 💬 集成Ollama对话功能（需要单独安装依赖）
- 更多功能更新中~~~ 🌱

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
- **Ollama对话依赖**：`ollama` - 用于Ollama聊天功能（可通过 `pip install ollama` 安装）

## 配置项
**可能会有多个网站的APIKEY所以通过网站名字命名** 
SHWGIJapi网址:[https://api.shwgij.com/](https://api.shwgij.com/user/register?cps=0vr22dJY)

在 `.env.prod` 文件中添加以下配置：

```env
# 黄历API配置
LUNAR_CALENDAR_API_KEY="您的API密钥"

# 新闻API配置
# 新闻更多配置请直接参考官方文档，如果你的配置获取不到API可以自行下载插件用AI帮你修改代码
SHWGIJ_API_KEY="您的新闻API密钥"

# 定时任务配置
# 格式: 分 时 日 月 周
SHWGIJ_CRON_EXPRESSION="0 8 * * *"
# 定时任务发送的群聊ID列表，多个群ID用逗号分隔
SHWGIJ_SEND_GROUPS="群聊ID1,群聊ID2"
# 是否启用定时任务，1-启用，0-禁用
SHWGIJ_CRON_ENABLE=1

# 日志级别配置 (可选：DEBUG, INFO, WARNING, ERROR)
SHWGIJ_LOG_LEVEL="INFO"
# 图片删除延时时间（秒）
SHWGIJ_IMAGE_DELETE_DELAY=120
# 缓存文件保留天数
SHWGIJ_CACHE_EXPIRE_DAYS=7

# Ollama配置（可选，如果需要使用聊天功能）
OLLAMA_API_KEY="您的Ollama API密钥（如果有）"
```

## 使用说明

### 黄历功能
- 文本版黄历：发送 `文字黄历` 或 `文本黄历`（无需 `/` 前缀）
- 图片版黄历：发送 `黄历`（无需 `/` 前缀）
- 兼容原有命令格式：`/文字黄历`、`@机器人 文字黄历`、`/黄历` 仍然可用

### 新闻功能
- 热榜新闻图片：发送 `/新闻图片` 获取今日热榜新闻图片

### 帮助功能
- 获取所有命令帮助：发送 `帮助`、`插件帮助` 或 `xihelp`（无需 `/` 前缀），或使用 `/帮助`、`/插件帮助`、`/xihelp`

### 测试功能
- 插件功能测试：发送 `/测试黄历` 测试插件功能

### Ollama聊天功能（扩展功能）
**注意：使用此功能前请先安装Ollama依赖** (`pip install ollama`)
- 清理对话历史：发送 `/清理历史` 或 `/重置对话`
- 更多Ollama相关命令请参考插件内部实现

## 许可证

本项目使用 [MIT](LICENSE) 许可证

## 致谢

感谢所有为本项目做出贡献的开发者！