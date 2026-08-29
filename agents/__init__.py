"""OpsPilot 领域 Agent 层：LangGraph 3 Agent 编排（Triage / Retrieval / Action）。

- state.py    GraphState 共享状态
- nodes.py    Agent 与控制节点实现
- graph.py    StateGraph 编排 + run_ticket 外部入口
- llm.py      LLM 抽象（deepseek / rule 双驱动可切换）
- rule_only.py 规则驱动分类（离线可复现）
"""
# 本机 AppLocker 拦截 xxhash 原生 DLL 时，注入纯 Python 兜底（正常机器不生效）
from agents import _xxhash_fallback  # noqa: F401