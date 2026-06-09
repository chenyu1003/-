"""
柳如烟的记忆系统
- 用户画像（长期，JSON 持久化）
- 近期对话日志（短期，JSON 持久化）
- 历史对话摘要（长期，JSON 持久化）
"""

from __future__ import annotations

import json
import os
from datetime import datetime


class MemorySystem:
    """管理柳如烟对用户的长期记忆。"""

    MAX_RECENT_EXCHANGES = 20   # 保留最近 N 轮对话原文
    MAX_PROFILE_ENTRIES = 50    # 画像最多保留 N 条事实
    PROFILE_UPDATE_INTERVAL = 8  # 每 N 轮对话后触发一次画像提取
    COMPACT_THRESHOLD = 30       # 超过此轮数时压缩旧对话为摘要

    def __init__(self, data_dir: str = ""):
        if not data_dir:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_data")
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        self.profile_path = os.path.join(self.data_dir, "user_profile.json")
        self.history_path = os.path.join(self.data_dir, "conversation_log.json")
        self.summary_path = os.path.join(self.data_dir, "conversation_summary.json")

        self.profile: dict[str, str] = self._load_json(self.profile_path, {})
        self.history: list[dict] = self._load_json(self.history_path, [])
        self.summaries: list[str] = self._load_json(self.summary_path, [])
        self._exchange_count_since_update = 0
        self._total_exchanges = len(self.history)

    # ----------------------------------------------------------
    # 文件 I/O
    # ----------------------------------------------------------
    @staticmethod
    def _load_json(path: str, default):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return default
        return default

    @staticmethod
    def _save_json(path: str, data) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ----------------------------------------------------------
    # 用户画像
    # ----------------------------------------------------------
    def update_profile(self, facts: dict[str, str]) -> None:
        """合并新事实到用户画像。"""
        if not facts:
            return
        self.profile.update(facts)
        # 超过上限时删掉最旧的条目
        while len(self.profile) > self.MAX_PROFILE_ENTRIES:
            oldest = next(iter(self.profile))
            del self.profile[oldest]
        self._save_json(self.profile_path, self.profile)

    def get_profile_context(self) -> str:
        """将用户画像格式化为上下文字符串。"""
        if not self.profile:
            return ""
        lines = []
        for key, value in self.profile.items():
            lines.append(f"- {key}：{value}")
        return "\n".join(lines)

    # ----------------------------------------------------------
    # 对话日志
    # ----------------------------------------------------------
    def add_exchange(self, user_msg: str, assistant_msg: str) -> None:
        """记录一轮对话。"""
        self.history.append({
            "user": user_msg,
            "assistant": assistant_msg,
            "time": datetime.now().isoformat(),
        })
        self._total_exchanges += 1
        self._exchange_count_since_update += 1
        self._save_json(self.history_path, self.history)

    def get_recent_history(self) -> str:
        """获取最近 N 轮对话的格式化文本。"""
        recent = self.history[-self.MAX_RECENT_EXCHANGES :] if self.history else []
        if not recent:
            return ""
        lines = []
        for entry in recent:
            lines.append(f"用户：{entry['user']}")
            lines.append(f"如烟：{entry['assistant']}")
        return "\n".join(lines)

    def should_update_profile(self) -> bool:
        """是否该从最近对话中提取新的用户画像了。"""
        return self._exchange_count_since_update >= self.PROFILE_UPDATE_INTERVAL

    def reset_profile_update_counter(self) -> None:
        self._exchange_count_since_update = 0

    def should_compact(self) -> bool:
        """是否需要压缩旧对话。"""
        return len(self.history) > self.COMPACT_THRESHOLD

    def compact_history(self, summary_text: str) -> None:
        """
        压缩对话历史：保留最近 MAX_RECENT_EXCHANGES 轮，
        将更早的对话替换为摘要存入 summaries。
        """
        if not self.history or len(self.history) <= self.COMPACT_THRESHOLD:
            return
        # 保留最近的
        keep = self.history[-self.MAX_RECENT_EXCHANGES:]
        # 被压缩的部分 + 新摘要
        self.summaries.append(summary_text)
        while len(self.summaries) > 10:
            self.summaries.pop(0)
        self.history = keep
        self._save_json(self.history_path, self.history)
        self._save_json(self.summary_path, self.summaries)

    def get_summaries_context(self) -> str:
        """获取历史摘要的格式化文本。"""
        if not self.summaries:
            return ""
        lines = ["【更早的聊天记忆】"]
        for i, s in enumerate(self.summaries, 1):
            lines.append(f"{i}. {s}")
        return "\n".join(lines)

    # ----------------------------------------------------------
    # 综合上下文
    # ----------------------------------------------------------
    def get_full_context(self) -> str:
        """
        构建给 LLM 的完整记忆上下文，包括：
        1. 历史摘要
        2. 用户画像
        3. 近期对话
        """
        parts = []

        summaries = self.get_summaries_context()
        if summaries:
            parts.append(summaries)

        profile = self.get_profile_context()
        if profile:
            parts.append(f"【用户画像】\n{profile}")

        recent = self.get_recent_history()
        if recent:
            parts.append(f"【最近聊天记录】\n{recent}")

        return "\n\n".join(parts)

    # ----------------------------------------------------------
    # 清空（重置对话，但保留画像）
    # ----------------------------------------------------------
    def reset_conversation(self) -> None:
        """重置当前对话（保留用户画像和摘要）。"""
        self.history = []
        self._exchange_count_since_update = 0
        self._save_json(self.history_path, [])
