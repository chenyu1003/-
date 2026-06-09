"""
柳如烟 — 虚拟网友
启动：python app.py  →  浏览器打开 http://127.0.0.1:7860
"""

import gradio as gr

from agent import VirtualFriend

friend = VirtualFriend(verbose=False)


def respond(message: str, history: list) -> tuple[str, list]:
    """处理用户消息，返回 (空输入框, 更新后的聊天记录)。"""
    if not message or not message.strip():
        return "", history
    reply = friend.chat(message.strip())["reply"]
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return "", history


def reset_chat() -> list:
    """重置对话，显示新问候。"""
    friend.reset_conversation()
    greeting = friend.get_greeting()
    return [{"role": "assistant", "content": greeting}]


def show_profile():
    text = friend.memory.get_profile_context()
    if not text:
        return "柳如烟还不太了解你哦，多聊聊吧～ 😊"
    return text


def show_memory():
    summaries = friend.memory.get_summaries_context()
    recent = friend.memory.get_recent_history()
    parts = []
    if summaries:
        parts.append(summaries)
    if recent:
        parts.append(f"【最近对话】\n{recent}")
    return "\n\n".join(parts) if parts else "还没有聊天记录～"


# ============================================================
# UI
# ============================================================
CSS = """
html, body, .gradio-container { height: 100%; margin: 0; padding: 0; }
footer { display: none; }
"""

with gr.Blocks(title="柳如烟") as demo:

    # ---- 标题 ----
    gr.Markdown("## 👩‍💻 柳如烟  *19岁 · 计算机大二 · 你的网友*")

    # ---- 聊天区 ----
    chatbot = gr.Chatbot(
        value=[],
        height=560,
        label="",
        show_label=False,
    )

    # ---- 输入行 ----
    with gr.Row():
        msg = gr.Textbox(
            placeholder="输入消息，按 Enter 发送...",
            scale=8,
            container=False,
            show_label=False,
        )
        send = gr.Button("发送", variant="primary", scale=1, min_width=80)

    # ---- 功能按钮 ----
    with gr.Row():
        profile_btn = gr.Button("📋 查看画像", size="sm")
        memory_btn = gr.Button("🧠 查看记忆", size="sm")
        reset_btn = gr.Button("🔄 重置对话", size="sm")

    info_box = gr.Textbox(
        label="信息",
        lines=8,
        interactive=False,
        visible=False,
    )

    # ---- 事件绑定 ----
    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    send.click(respond, [msg, chatbot], [msg, chatbot])

    reset_btn.click(reset_chat, outputs=[chatbot])

    def _open_profile():
        return gr.update(value=show_profile(), visible=True)

    def _open_memory():
        return gr.update(value=show_memory(), visible=True)

    profile_btn.click(fn=_open_profile, outputs=[info_box])
    memory_btn.click(fn=_open_memory, outputs=[info_box])


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        css=CSS,
        theme=gr.themes.Soft(),
    )
