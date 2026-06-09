# 👩‍💻 柳如烟 — 虚拟网友

一个基于 DeepSeek 大模型的虚拟网友聊天机器人。

**柳如烟**：19 岁计算机专业大二女生，性格幽默温柔理性热情，口语化聊天风格，会记住关于你的事。

---

## 快速开始

### 1. 获取 API Key

去 [DeepSeek 开放平台](https://platform.deepseek.com) 注册账号，获取 API Key（新用户有免费额度）。

### 2. 配置

打开 `.env` 文件，填入你的 API Key：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

其他配置项一般不需要改动：
- `DEEPSEEK_BASE_URL`：DeepSeek API 地址（默认 `https://api.deepseek.com/v1`）
- `DEEPSEEK_MODEL`：模型名（默认 `deepseek-chat`，即 DeepSeek-V3）

### 3. 安装依赖

打开终端（见下方说明），输入：

```bash
pip install -r requirements.txt
```

### 4. 启动

在终端中输入：

```bash
python app.py
```

看到 `Running on local URL: http://127.0.0.1:7860` 后，浏览器打开这个地址即可开始聊天。

---

## ⚠️ 如何正确启动（重要）

**千万不要双击 `app.py` 文件！** 那样窗口会一闪而过，什么也看不到。

正确做法：

### Windows

1. 打开项目文件夹 `Personal Agent`
2. 在文件夹的**地址栏**里输入 `cmd`，按回车（会弹出命令行窗口）
3. 在命令行中输入 `python app.py`，按回车
4. **保持命令行窗口打开**，不要关掉
5. 打开浏览器，访问 `http://127.0.0.1:7860`

### 手动打开终端

如果地址栏输入 cmd 不生效，可以：

- 按 `Win + R`，输入 `cmd`，回车
- 在命令行中输入以下命令切换到项目目录：
  ```cmd
  cd /d "F:\结课报告\Personal Agent"
  ```
- 然后输入 `python app.py`，回车

### 结束运行

在终端里按 `Ctrl + C` 即可停止程序。

---

## 项目结构

```
Personal Agent/
├── .env                    # API Key 配置（需自行填写）
├── requirements.txt        # Python 依赖
├── app.py                  # Gradio Web UI 入口
├── agent.py                # VirtualFriend 核心类
├── persona.py              # 柳如烟人设 Prompt
├── memory.py               # 记忆系统
├── tools.py                # 工具（天气、日期、时间）
├── memory_data/            # 长期记忆存储（自动生成）
│   ├── user_profile.json   # 用户画像
│   ├── conversation_log.json    # 近期对话记录
│   └── conversation_summary.json # 历史对话摘要
└── README.md               # 本文件
```

---

## 功能说明

### 💬 聊天

- 像朋友一样自然聊天，口语化风格，使用表情符号和网络用语
- 柳如烟有自己的"人设"：养不活的盆栽"小绿"、爱喝杨枝甘露、追番《葬送的芙莉莲》……

### 🧠 记忆

- **短期记忆**：记住本次对话的前文
- **长期记忆**：从对话中提取你的画像（名字、爱好、习惯等），下次打开还记得
- **主动回忆**：会在合适的时候自然提起"你上次说过……"

### 🛠 工具

柳如烟可以调用以下工具获取实时信息：

| 工具 | 功能 | 示例 |
|------|------|------|
| `get_weather` | 查询城市天气 | "北京今天天气怎么样？" |
| `get_date` | 查询日期和星期 | "今天几号？" |
| `get_time` | 查询精确时间 | "现在几点了？" |

### 🎛 界面按钮

| 按钮 | 功能 |
|------|------|
| 发送 ✨ | 发送消息 |
| 🔄 重新生成 | 重新生成上一条回复 |
| ↩ 撤回 | 撤回上一条消息 |
| 🗑 清屏 | 清除聊天显示 |
| 📋 查看我的画像 | 查看柳如烟对你了解多少 |
| 🔁 重置对话 | 清空当前对话（保留画像） |

---

## 自定义

### 修改人设

编辑 `persona.py` 中的 `PERSONA_SYSTEM_PROMPT`，可以改变柳如烟的性格、背景和说话风格。

### 添加工具

1. 在 `tools.py` 中实现工具函数
2. 在 `agent.py` 的 `_TOOLS_SCHEMA` 中添加工具定义
3. 在 `agent.py` 的 `_execute_tool` 中添加工具路由

### 调整记忆

编辑 `memory.py` 中的参数：
- `MAX_RECENT_EXCHANGES`：保留最近 N 轮对话原文（默认 20）
- `PROFILE_UPDATE_INTERVAL`：每 N 轮对话提取一次画像（默认 8）
- `COMPACT_THRESHOLD`：对话超过 N 轮时压缩旧对话（默认 30）

---

## 常见问题

**Q: 启动报错 "请设置环境变量 DEEPSEEK_API_KEY"**

A: 检查 `.env` 文件是否填写了正确的 API Key。

**Q: 聊天回复乱码或报错**

A: 检查网络是否能访问 `https://api.deepseek.com`，以及 API Key 是否还有余额。

**Q: 记忆文件在哪里？**

A: 在 `memory_data/` 目录下。删除该目录即可清除所有记忆（包括用户画像）。

**Q: 可以分享给别人用吗？**

A: 可以。把整个文件夹发给对方，对方需要：
1. 安装 Python 3.10+
2. `pip install -r requirements.txt`
3. 自己申请 DeepSeek API Key 填入 `.env`
4. `python app.py`

---

## 技术栈

- **大模型**：DeepSeek-V3（OpenAI 兼容接口）
- **Agent 框架**：LangChain（消息管理 + 工具绑定）
- **Web UI**：Gradio ChatInterface
- **记忆存储**：本地 JSON 文件
- **天气数据**：wttr.in（免费免注册）
