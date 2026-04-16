# app.py
import streamlit as st
import os
from agent import run_agent

# 页面配置
st.set_page_config(page_title="自主智能体平台", page_icon="🤖", layout="wide")
st.title("🤖 任务自主完成智能体")
st.markdown("通过自然语言与我交互，我将自动调用工具（搜索、处理数据、导出Excel等）帮你完成任务。")

# 初始化历史对话记录
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system",
         "content": "你是用户的全能AI助手。你需要根据用户需求自主决定调用工具。如果生成了文件，请在回复中告知用户到侧边栏下载。"}
    ]

# 侧边栏：文件下载区
with st.sidebar:
    st.header("📂 产出文件下载区")
    st.markdown("工具生成的文件会出现在这里：")

    # 动态扫描 outputs 文件夹中的文件
    if os.path.exists("outputs"):
        files = os.listdir("outputs")
        if files:
            for file in files:
                filepath = os.path.join("outputs", file)
                with open(filepath, "rb") as f:
                    st.download_button(
                        label=f"⬇️ 下载 {file}",
                        data=f,
                        file_name=file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info("暂无生成的文件")

# 展示历史对话 (过滤掉 system 和 tool 的内部通信内容，只给用户看干净的对话)
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user", avatar="👤").write(msg["content"])
    elif msg["role"] == "assistant" and msg.get("content"):
        st.chat_message("assistant", avatar="🤖").write(msg["content"])
    elif msg["role"] == "tool":
        # 也可以选择把工具调用的日志折叠显示给用户看
        with st.expander(f"⚙️ 工具调用完成: {msg['name']}"):
            st.write(msg["content"])

# 用户输入区域
if prompt := st.chat_input("请输入你的要求，例如：搜索最新AI大模型信息并生成Excel表格总结"):
    # 1. 页面显示用户消息
    st.chat_message("user", avatar="👤").write(prompt)

    # 2. 将消息存入状态
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 3. 调用智能体核心
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🧠 AI思考并调度工具中..."):
            # 获取AI最终回复并更新消息历史
            final_reply, updated_messages = run_agent(st.session_state.messages)
            st.session_state.messages = updated_messages

            # 显示结果
            st.write(final_reply)

    # 刷新页面以更新侧边栏的文件下载按钮
    st.rerun()