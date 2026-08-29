#!/bin/sh
# OpsPilot 容器启动脚本：
#   1) 重建确定性仿真数据集（data/generated）
#   2) 按需生成评测基线报告（reports/eval.json，rule 驱动离线可复现）
#   3) 以 CMD 启动 uvicorn，托管 API + 前端 SPA
set -e

echo "[OpsPilot] 生成仿真数据集 (seed=42, 确定性可复现)"
python -m data_generation.generate || { echo "数据生成失败"; exit 1; }

echo "[OpsPilot] 运行评测基线 (rule 驱动 / 离线)"
mkdir -p reports
python -m eval.evaluator --driver rule --out reports/eval.json \
    || echo "[OpsPilot] 评测可选，失败不阻断启动"

echo "[OpsPilot] 启动服务 → http://0.0.0.0:8000  (LLM_DRIVER=${LLM_DRIVER:-rule})"
exec "$@"