"""
柳如烟的工具集：天气、日期、时间
"""

from datetime import datetime, timezone

import requests
from langchain_core.tools import StructuredTool


# ============================================================
# 天气查询（wttr.in，免费免注册）
# ============================================================
def _get_weather_impl(city: str) -> str:
    """
    通过 wttr.in 获取指定城市的天气信息。
    返回简洁的天气描述。
    """
    city = (city or "北京").strip()
    try:
        url = f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=zh"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            raw = resp.text.strip()
            # 解析：天气状况 温度 湿度 风力
            # 例如：晴 +28°C 45% 东南风 3级
            return f"城市：{city}，{raw}"
        else:
            return f"天气查询失败（HTTP {resp.status_code}），请稍后重试。"
    except requests.RequestException as e:
        return f"天气查询出错：{e}。建议用户稍后重试。"


def _get_weather_for_tool(action_input: str) -> str:
    """查询指定城市的天气。输入：城市名（如 北京、上海、深圳）。"""
    return _get_weather_impl((action_input or "").strip())


# ============================================================
# 日期和时间查询
# ============================================================
def _get_date_impl() -> str:
    """返回当前日期（含星期）。"""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    wd = weekdays[now.weekday()]
    return f"今天是 {now.year}年{now.month}月{now.day}日，{wd}"


def _get_date_for_tool(_action_input: str = "") -> str:
    """查询今天的日期和星期。输入：无。"""
    return _get_date_impl()


def _get_time_impl() -> str:
    """返回当前时间。"""
    now = datetime.now()
    return f"现在是 {now.hour:02d}:{now.minute:02d}:{now.second:02d}"


def _get_time_for_tool(_action_input: str = "") -> str:
    """查询当前精确时间。输入：无。"""
    return _get_time_impl()


# ============================================================
# 工具注册
# ============================================================
def build_friend_tools() -> list:
    """创建柳如烟可用的工具列表。"""
    return [
        StructuredTool.from_function(
            func=_get_weather_for_tool,
            name="get_weather",
            description="查询指定城市的当前天气（温度、湿度、风力、天气状况）。输入为城市名，如 北京、上海、深圳、杭州。",
        ),
        StructuredTool.from_function(
            func=_get_date_for_tool,
            name="get_date",
            description="查询今天的日期和星期。不需要输入。",
        ),
        StructuredTool.from_function(
            func=_get_time_for_tool,
            name="get_time",
            description="查询当前的精确时间（时:分:秒）。不需要输入。",
        ),
    ]


def get_current_time_context() -> str:
    """获取当前时间上下文字符串，用于注入提示词。"""
    now = datetime.now()
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    wd = weekdays[now.weekday()]
    part_of_day = (
        "凌晨" if now.hour < 6
        else "早上" if now.hour < 9
        else "上午" if now.hour < 12
        else "中午" if now.hour < 14
        else "下午" if now.hour < 18
        else "晚上" if now.hour < 22
        else "深夜"
    )
    return f"{now.year}年{now.month}月{now.day}日 {wd} {part_of_day} {now.hour:02d}:{now.minute:02d}"
