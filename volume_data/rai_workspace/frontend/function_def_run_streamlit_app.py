
from langchain_core.callbacks.base import BaseCallbackHandler
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import Runnable

from rai.agents.integrations.streamlit import get_streamlit_cb, streamlit_invoke
from rai.messages import HumanMultimodalMessage

from rai.agents.langchain import (
    ReActAgentState,
)


def run_streamlit_app(agent: Runnable[ReActAgentState, ReActAgentState], page_title: str, initial_message: str):
    st.title(page_title)
    st.markdown("---")

    st.sidebar.header("Tool Calls History")

    if "graph" not in st.session_state:
        st.session_state["graph"] = agent

    if "messages" not in st.session_state:
        st.session_state["messages"] = [AIMessage(content=initial_message)]

    prompt: str | None = st.chat_input()
    for msg in st.session_state.messages:
        if isinstance(msg, AIMessage):
            if msg.content:
                st.chat_message("assistant").write(msg.content)
        elif isinstance(msg, HumanMultimodalMessage):
            continue
        elif isinstance(msg, HumanMessage):
            st.chat_message("user").write(msg.content)
        elif isinstance(msg, ToolMessage):
            with st.sidebar.expander(f"Tool: {msg.name}", expanded=False):
                st.code(msg.content, language="json")

    if prompt:
        st.session_state.messages.append(HumanMessage(content=prompt))
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            st_callback: BaseCallbackHandler = get_streamlit_cb(st.container())
            streamlit_invoke(
                st.session_state["graph"], st.session_state.messages, [st_callback] # type: ignore
            )
    




