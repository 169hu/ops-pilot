# OpsPilot 多阶段构建
#   stage 1 (node) · 构建 React 前端 → ui/dist
#   stage 2 (python) · 运行时镜像，前端产物由后端同一端口托管
#
# 启动时由 docker/entrypoint.sh 重新生成数据集并按需跑评测基线，镜像内不含
# 本地生成产物（data/generated、reports），保证「一条镜像到处可复现」。

# ---------------- 阶段 1：构建前端 ----------------
FROM node:20-alpine AS ui-builder
WORKDIR /app
COPY ui/package.json ui/package-lock.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY ui/ ./
RUN npm run build

# ---------------- 阶段 2：Python 运行时 ----------------
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    LLM_DRIVER=rule \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# 编译依赖（psycopg/pgvector 走 C 扩展）+ 健康检查用 curl
# -o Acquire::Retries / --fix-missing：公网 debian 源偶发断连，加重试增强健壮性
RUN apt-get update && apt-get install -y -o Acquire::Retries=8 --fix-missing --no-install-recommends \
        gcc libpq-dev libffi-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --timeout 60 \
    -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 复制业务代码 + 阶段1的前端产物
COPY . .
COPY --from=ui-builder /app/dist ./ui/dist

# 启动前清掉本地生成产物，由 entrypoint 重建，确保容器内数据自洽
RUN rm -rf data/generated reports results

RUN chmod +x docker/entrypoint.sh
EXPOSE 8000

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]