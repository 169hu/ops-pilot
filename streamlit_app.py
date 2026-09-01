"""OpsPilot 运维助手 · Streamlit Cloud 展示入口

云端（免费云实例）无法承载 FastAPI + React + pgvector + Redis 的完整后端，
因此本页为「成果展示 + 轻量对话」：
- 展示黄金用例评测指标（意图/风险/工具选择准确率、安全门禁拦截率）
- 提供基于 DeepSeek API 的运维对话演示（Secrets 配置 DEEPSEEK_API_KEY 后启用）
完整功能版请在本机运行 docker-compose 或 uvicorn。
"""
import json
import os
from pathlib import Path

import streamlit as st

# ============ Streamlit Cloud 适配 ============
try:
    for _k, _v in st.secrets.items():
        if _k.isupper() and not os.environ.get(_k):
            os.environ[_k] = str(_v)
except Exception:
    pass

st.set_page_config(page_title="OpsPilot 运维助手", page_icon="🚀", layout="wide")

st.markdown(
    """
<style>
    :root { --navy: #1F3E6E; --paper: #F6F4EF; }
    html, body, [class*="css"], [data-testid="stHeader"] {
        background: transparent;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                     "Microsoft YaHei", sans-serif;
    }
    [data-testid="stAppViewContainer"], .stApp {
        background: #F6F4EF;
    }
    h1, h2, h3, h4 { font-family: "Songti SC", "STSong", "SimSun", "Noto Serif SC", serif; }
    .metric-card {
        background: #FDFBF7; border: 1px solid #E2DCD0;
        border-radius: 6px; padding: 1.1rem; text-align: center;
        transition: border-color 0.2s;
    }
    .metric-card:hover { border-color: var(--navy); }
    .metric-score { font-size: 1.8rem; font-weight: 700; color: var(--navy); }
    .metric-label { font-size: 0.8rem; color: #6B655B; margin-top: 0.25rem; }
    .ok { color: #3E6B4F; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("OpsPilot 运维助手")
st.caption("多 Agent 运维自动化 · 工具网关 + 安全门禁 · 黄金用例评测")

# ============ 1) 评测指标 ============
with st.container(border=True):
    st.subheader("黄金用例评测（离线预生成）")
    eval_path = Path(__file__).resolve().parent / "reports" / "eval.json"
    try:
        with open(eval_path, encoding="utf-8") as f:
            eval_data = json.load(f)
        metrics = eval_data.get("metrics", {})
        gates = eval_data.get("gates", {})

        m_labels = {
            "intent_accuracy": "意图识别",
            "risk_accuracy": "风险分级",
            "tool_selection_accuracy": "工具选择",
            "tool_param_accuracy": "参数填充",
            "final_status_accuracy": "终态判定",
            "rag_hit_rate": "RAG 命中率",
            "avg_response_s": "平均响应(s)",
        }
        cols = st.columns(4)
        for i, (key, label) in enumerate(m_labels.items()):
            val = metrics.get(key, "—")
            if isinstance(val, float):
                val = f"{val:.2f}"
            cols[i % 4].markdown(
                f'<div class="metric-card"><div class="metric-score">{val}</div>'
                f'<div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

        g_labels = {
            "attack_intercept_rate": "攻击拦截率",
            "injection_block_rate": "注入拦截率",
            "sensitive_block_rate": "敏感拦截率",
            "unauthorized_block_rate": "越权拦截率",
        }
        st.markdown("##### 安全门禁（红线）")
        gcols = st.columns(4)
        for i, (key, label) in enumerate(g_labels.items()):
            val = gates.get(key, "—")
            ok = val == 1.0
            if isinstance(val, float):
                val = f"{val:.0%}"
            gcols[i % 4].markdown(
                f'<div class="metric-card"><div class="metric-score {"" if not ok else "ok"}">{val}</div>'
                f'<div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True,
            )
        with st.expander("评测详情"):
            detail = eval_data.get("detail", {})
            total = detail.get("golden", {}).get("total", 0)
            st.caption(f"黄金用例总数：{total}")
            st.markdown(
                "- 意图/风险/工具/参数/终态五维打分 + RAG 命中率 + 响应耗时\n"
                "- 红线门禁：注入/敏感/越权/攻击 4 项拦截率必须 100% 才允许发布"
            )
    except Exception as e:
        st.warning(f"评测文件读取失败：{e}")

# ============ 2) 轻量对话演示 ============
with st.container(border=True):
    st.subheader("运维对话演示（DeepSeek API）")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        st.info("未配置 DEEPSEEK_API_KEY，对话功能不可用；请在 Streamlit Secrets 中配置。")
    else:
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        if "msgs" not in st.session_state:
            st.session_state.msgs = []
        for m in st.session_state.msgs:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if prompt := st.chat_input("例如：请开通我对 GitLab ops-backend 的写权限"):
            st.session_state.msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                try:
                    resp = client.chat.completions.create(
                        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                        messages=[
                            {"role": "system",
                             "content": "你是 OpsPilot 运维助手。模拟安全运维流程：先识别意图与风险级，"
                             "再按权限策略处理，对高敏操作给出审批提示。用中文简洁回答。",
                             },
                            *st.session_state.msgs,
                        ],
                        temperature=0.3,
                        max_tokens=512,
                    )
                    answer = resp.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.msgs.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"调用失败：{e}")

st.caption("完整版（FastAPI + React + 审批流）请在本机运行 docker-compose；云端为展示版。")