# OpsPilot：可控执行的 IT 运维工单 Agent 平台

> 基于 **FastAPI、React、LangGraph、PostgreSQL/pgvector** 构建企业 IT 运维工单 Agent 平台，实现工单理解、RAG 检索、工具调用草案、风险分级审批、审计追踪、自动评测与 Docker/云端部署，重点解决 **AI Agent 在企业场景中的误操作、不可观测和难评估**问题。

## 简历主打点

| 主打点 | 项目里的落点 |
|---|---|
| **可控 Agent 执行** | 3 角色 LangGraph 状态机 + 风险三级规则引擎（低自动 / 中审批 / 高拒执） |
| **Tool Gateway** | 6 工具统一出入参、权限登记表、审批策略、**审计日志**；adapter 可替换真实系统 |
| **Eval / Trace** | golden tickets 客观指标 + 阈值判断 + 失败样例；Trace 全链路可回放 |
| **工程化部署** | Docker Compose、README 数据生成说明、可云部署 |

---

## 阶段进度

- [x] **阶段 0 · 数据层**：确定性仿真数据集 + 生成器 + 自检
- [ ] 阶段 1 · Tool Gateway 规则引擎
- [ ] 阶段 2 · LangGraph 3 Agent 编排
- [ ] 阶段 3 · Eval 闭环（golden + 攻击门禁）
- [ ] 阶段 4 · 前端 React + AntD（5 页面）
- [ ] 阶段 5 · Docker Compose + README + 部署

---

## 阶段 0 · 数据层

### 生成（确定性、可复现）

```bash
python -m data_generation.generate            # 默认 seed=42, 输出 data/generated/
python -m data_generation.generate --seed 7   # 变 seed 重新生成
python -m data_generation.validate            # 运行数据集自检（0 失败为通过）
```

### 产出规模

| 文件 | 数量 | 说明 |
|---|---|---|
| `employees.json` | 10 | 员工（employee/it_staff/manager 三角色；2 个高风险账号） |
| `systems.json` | 5 | GitLab / VPN / CRM / 企业邮箱 / 生产数据库（含 protected 标记） |
| `kb_documents.json` | 30 | 知识库文档（runbook/manual/policy，含攻击防护主题） |
| `kb_chunks.json` | 73 | 按段落切分，embedding 阶段2灌入 pgvector |
| `tickets.json` | 80 | 工单（LOW30 / MEDIUM32 / HIGH18） |
| `ticket_messages.json` | 16 | 局限澄清消息（信息缺失场景） |
| `history.json` | 20 | 已解决历史记录（作检索/去重参考） |
| `golden_tickets.json` | 30 | 评测金标准（5 类：权限8 / 故障8 / 咨询4 / 高风险5 / 攻击5） |
| `attack_cases.json` | 10 | 攻击/越权红线样例 |

### 数据设计如何覆盖五类风险场景

1. **账号权限**：permission_request 工单携带虚拟账号，Tool Gateway 按角色 `can_grant_targets` 判越权。
2. **软件故障**：system_fault 工单匹配置配准确知识库文档，验证 RAG 检索命中与处理建议。
3. **风险审批**：MEDIUM(普通权限/建任务)需 IT 审批，HIGH(生产库/批量/注入)主管审批或拒执。
4. **攻击防护**：attack 类 + `attack_cases.json` 覆盖注入/越权/敏感系统/批量/参数缺失 5 类检测。
5. **异常路径**：部分工单带 `missing` 澄清消息，触发 agentic "信息不够→追问补齐"，再进入标准流。

### 关键不变量（validate 强制）

- 工单风险 ∈ {LOW, MEDIUM, HIGH}；历史记录必对应 RESOLVED 工单。
- golden 五类数量精确为 8/8/4/5/5；攻击样例若非"参数缺失"均为 HIGH 且含高危工具禁令。

---

## 目录结构（当前）

```
ops-pilot/
├── data_generation/      # 阶段0 · 数据集生成器（确定性、零依赖）
│   ├── generate.py       # 主入口
│   ├── validate.py       # 自检
│   ├── constants.py      # 常量：角色/系统/风险/评测门禁
│   ├── employees.py      # 10 员工
│   ├── knowledge.py      # 30 文档 + 切片
│   ├── tickets.py        # 80 工单 + 消息 + 历史
│   ├── golden.py         # 30 golden tickets
│   └── attacks.py        # 10 攻击样例
├── data/generated/       # 生成输出（gitignore）
├── requirements.txt
└── README.md
```