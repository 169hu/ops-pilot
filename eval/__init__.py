"""阶段3 · Eval 闭环：golden 能力评测 + 攻击红线门禁。

能力指标（soft targets）：
  intent_accuracy / risk_accuracy / tool_selection_accuracy
  tool_param_accuracy / final_status_accuracy
红线门禁（publish gate，须 100%）：
  注入拦截率、敏感系统拦截率、越权拦截率、禁止工具调用违规数。
"""