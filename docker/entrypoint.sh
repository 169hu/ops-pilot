#!/bin/sh
# OpsPilot 容器启动脚本：
#   1) 重建确定性仿真数据集（data/generated）
#   2) 按需生成评测基线报告（reports/eval.json，rule 驱动离线可复现）
#   3) 以 CMD 启动 uvicorn，托管 API + 前端 SPA
set -e

echo "[OpsPilot] 生成仿真数据集 (seed=42, 确定性可复现)"
python -m data_generation.generate || { echo "数据生成失败"; exit 1; }

# 评测子进程单独指定驱动：默认 rule(离线可复现、启动快)，设 EVAL_DRIVER=deepseek 可生成真实 LLM 报告。
# 注意必须用子进程环境变量 LLM_DRIVER 固化，因为 agents/llm 在 import 时冻结驱动，
# 仅靠这里改不会影响上方 uvicorn 进程的运行驱动(仍为 LLM_DRIVER=deepseek)。
EVAL_DRIVER="${EVAL_DRIVER:-rule}"
echo "[OpsPilot] 运行评测基线 (driver=${EVAL_DRIVER}; 可选,失败不阻断)"
mkdir -p reports
LLM_DRIVER="${EVAL_DRIVER}" python -m eval.evaluator --driver "${EVAL_DRIVER}" --out reports/eval.json \
    || echo "[OpsPilot] 评测可选，失败不阻断启动"

echo "[OpsPilot] 启动服务 → http://0.0.0.0:8000  (LLM_DRIVER=${LLM_DRIVER:-rule})"
exec "$@"