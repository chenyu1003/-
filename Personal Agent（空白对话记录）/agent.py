"""
柳如烟 — VirtualFriend 核心 Agent
基于 DeepSeek 原生 function calling + 手动工具循环
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from persona import build_persona_prompt
from memory import MemorySystem
from tools import build_friend_tools, get_current_time_context

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# DeepSeek 配置
_DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
_DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _create_deepseek_llm(*, temperature: float = 0.7, max_tokens: int = 2048) -> ChatOpenAI:
    """创建 DeepSeek LLM 客户端（OpenAI 兼容接口）。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY（在 .env 文件中填写你的 DeepSeek API Key）。")
    return ChatOpenAI(
        api_key=api_key,
        base_url=_DEEPSEEK_BASE_URL,
        model=_DEEPSEEK_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=120,
        max_retries=2,
    )


# ============================================================
# 工具执行
# ============================================================
def _execute_tool(tool_name: str, tool_args: dict) -> str:
    """根据工具名和参数执行工具，返回结果字符串。"""
    from tools import (
        _get_weather_impl,
        _get_date_impl,
        _get_time_impl,
    )

    if tool_name == "get_weather":
        city = tool_args.get("city", "") or tool_args.get("location", "") or "北京"
        return _get_weather_impl(city)
    elif tool_name == "get_date":
        return _get_date_impl()
    elif tool_name == "get_time":
        return _get_time_impl()
    else:
        return json.dumps({"error": f"未知工具：{tool_name}"}, ensure_ascii=False)


# ============================================================
# 用户画像提取器
# ============================================================
_USER_INFO_EXTRACTION_PROMPT = """你是一个信息提取助手。请从以下对话中提取关于**用户**（不是 AI）的新信息。

规则：
1. 只提取关于用户本人的事实：姓名、昵称、年龄、职业、爱好、习惯、经历、喜好、计划、烦恼等
2. 每条信息用简短的 key: value 形式（如 "名字: 小明"、"爱好: 打篮球"）
3. 不要提取已经在【已有画像】中存在的重复信息
4. 如果对话中没有新的用户信息，返回空 JSON 对象 {}
5. 不要记录闲聊中随口提到的无关信息

已有画像：
{existing_profile}

近期对话：
{recent_conversation}

请用 JSON 格式输出：
{{"key1": "value1", "key2": "value2"}}"""


def _extract_user_facts(
    llm: ChatOpenAI,
    recent_conversation: str,
    existing_profile: str,
) -> dict[str, str]:
    """从近期对话中提取用户新事实。"""
    prompt = _USER_INFO_EXTRACTION_PROMPT.format(
        existing_profile=existing_profile or "（尚无画像）",
        recent_conversation=recent_conversation,
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content = (response.content or "").strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        facts = json.loads(content)
        if isinstance(facts, dict):
            return {str(k): str(v) for k, v in facts.items() if v}
        return {}
    except (json.JSONDecodeError, Exception):
        return {}


# ============================================================
# 对话摘要器
# ============================================================
_CONVERSATION_SUMMARY_PROMPT = """请用 2-4 句简短的中文总结以下对话的主要内容。重点记录：
- 用户提到了什么重要信息
- 聊了什么话题
- 有没有值得记住的关键事件

对话：
{conversation}

简短总结："""


def _summarize_conversation(llm: ChatOpenAI, conversation_text: str) -> str:
    """对一段对话进行简短摘要。"""
    prompt = _CONVERSATION_SUMMARY_PROMPT.format(conversation=conversation_text)
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        return (response.content or "").strip()
    except Exception:
        return ""


# ============================================================
# 工具定义（OpenAI function calling 格式）
# ============================================================
_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气（温度、湿度、风力、天气状况）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名，如 北京、上海、深圳、杭州",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_date",
            "description": "查询今天的日期和星期。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "查询当前的精确时间（时:分:秒）。",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


# ============================================================
# VirtualFriend — 核心 Agent
# ============================================================
class VirtualFriend:
    """柳如烟 — 虚拟网友智能体。"""

    MAX_TOOL_ROUNDS = 3  # 最多连续调用工具 3 轮

    def __init__(
        self,
        *,
        temperature: float = 0.7,
        verbose: bool = False,
    ):
        self.memory = MemorySystem()
        self.tools = build_friend_tools()  # 保留 LangChain Tool 引用（备用）
        self.verbose = verbose

        # 对话用的 LLM（温度略高，更有聊天感）
        self.chat_llm = _create_deepseek_llm(temperature=temperature, max_tokens=2048)
        # 提取/摘要用的 LLM（温度低，更准确）
        self.util_llm = _create_deepseek_llm(temperature=0, max_tokens=1024)

        # 绑定工具到聊天 LLM
        self.llm_with_tools = self.chat_llm.bind_tools(_TOOLS_SCHEMA)

    # ----------------------------------------------------------
    # 核心对话方法
    # ----------------------------------------------------------
    def chat(self, user_message: str) -> dict:
        """
        处理用户消息并返回回复。
        流程：
        1. 构建系统提示词（人设 + 记忆 + 时间）
        2. 通过 LLM + function calling 生成回复
        3. 记录对话并维护记忆
        """
        # 构建记忆上下文
        time_ctx = get_current_time_context()
        memory_ctx = self.memory.get_full_context()
        system_prompt = build_persona_prompt(
            memory_context=memory_ctx,
            current_time=time_ctx,
        )

        if self.verbose:
            print(f"\n{'='*50}")
            print(f"[系统提示词长度] {len(system_prompt)} chars")
            print(f"[用户消息] {user_message}")

        # 构建消息列表
        messages = [SystemMessage(content=system_prompt)]

        # 添加最近的对话历史（让模型有上下文连贯性）
        if self.memory.history:
            recent = self.memory.history[-6:]  # 最近 6 轮
            for entry in recent:
                messages.append(HumanMessage(content=entry["user"]))
                messages.append(SystemMessage(content=f"（你之前的回复）{entry['assistant']}"))

        messages.append(HumanMessage(content=user_message))

        # ---- function calling 循环 ----
        tool_calls_log = []
        for _round in range(self.MAX_TOOL_ROUNDS):
            response = self.llm_with_tools.invoke(messages)

            # 检查是否有工具调用
            tool_calls = getattr(response, "tool_calls", None) or []

            if not tool_calls:
                # 没有工具调用 → 这就是最终回复
                reply = (response.content or "").strip()
                if not reply:
                    reply = "诶，我好像走神了……你再说一遍？😅"
                if self.verbose:
                    print(f"[回复] {reply[:100]}...")
                break

            # 有工具调用 → 执行工具并追加结果
            messages.append(response)  # 把包含 tool_calls 的 AI 消息加入

            for tc in tool_calls:
                tool_name = tc.get("name", "")
                tool_args = tc.get("args", {})
                tool_id = tc.get("id", f"call_{_round}")

                if self.verbose:
                    print(f"[工具调用] {tool_name}({tool_args})")

                result = _execute_tool(tool_name, tool_args)
                tool_calls_log.append({
                    "round": _round + 1,
                    "tool": tool_name,
                    "args": json.dumps(tool_args, ensure_ascii=False),
                    "result": result[:120] + "..." if len(result) > 120 else result,
                })

                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
        else:
            # 超过最大轮数 → 强制要求最终回复
            if self.verbose:
                print("[警告] 超过最大工具轮数，强制回复")
            messages.append(HumanMessage(content="请不要再调用工具了，直接给出你的最终回复。"))
            final_response = self.chat_llm.invoke(messages)
            reply = (final_response.content or "").strip()
            if not reply:
                reply = "嗯…我想了一下，这个问题有点复杂，要不我们换个话题？😅"

        # 记录对话
        self.memory.add_exchange(user_message, reply)

        # 记忆维护
        self._maybe_update_profile()
        self._maybe_compact_history()

        return {
            "reply": reply,
            "tool_calls": tool_calls_log,
            "react_steps": len(tool_calls_log),
        }

    # ----------------------------------------------------------
    # 记忆维护
    # ----------------------------------------------------------
    def _maybe_update_profile(self) -> None:
        if not self.memory.should_update_profile():
            return
        recent = self.memory.get_recent_history()
        existing = self.memory.get_profile_context()
        facts = _extract_user_facts(self.util_llm, recent, existing)
        if facts:
            if self.verbose:
                print(f"[画像更新] {facts}")
            self.memory.update_profile(facts)
        self.memory.reset_profile_update_counter()

    def _maybe_compact_history(self) -> None:
        if not self.memory.should_compact():
            return
        keep_count = self.memory.MAX_RECENT_EXCHANGES
        to_compress = (
            self.memory.history[:-keep_count]
            if len(self.memory.history) > keep_count
            else []
        )
        if not to_compress:
            return
        text = "\n".join(
            f"用户：{e['user']}\n如烟：{e['assistant']}" for e in to_compress
        )
        summary = _summarize_conversation(self.util_llm, text)
        if summary:
            if self.verbose:
                print(f"[对话摘要] {summary}")
            self.memory.compact_history(summary)

    # ----------------------------------------------------------
    # 初始问候
    # ----------------------------------------------------------
    def get_greeting(self) -> str:
        """根据记忆和时间生成初始问候。"""
        time_ctx = get_current_time_context()
        profile = self.memory.get_profile_context()

        if not profile:
            return (
                "嗨！我叫柳如烟～一个学计算机的大二女生 🎓\n"
                "很高兴认识你！以后咱就是网友啦，叫我如烟就好～\n"
                "你呢？怎么称呼？😊"
            )

        prompt = f"""当前时间：{time_ctx}

关于用户的画像：
{profile}

你是柳如烟。用户回来了。请用一句简短、自然的问候欢迎ta，语气温暖随意。
根据画像提到一件关于用户的事，让问候有记忆感。不超过50字。"""

        try:
            response = self.chat_llm.invoke([HumanMessage(content=prompt)])
            return (response.content or "").strip()
        except Exception:
            return "嘿，你回来啦！今天怎么样？😊"

    # ----------------------------------------------------------
    # 重置（保留画像，清空当前对话）
    # ----------------------------------------------------------
    def reset_conversation(self) -> None:
        self.memory.reset_conversation()
