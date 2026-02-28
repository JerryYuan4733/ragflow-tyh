# ================================
# Stage 1: 前端构建
# ================================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# ================================
# Stage 2: 后端 + 前端产物
# ================================
FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir . 

# 后端代码
COPY backend/app ./app
# 迁移脚本（手动迁移/回滚用）
COPY backend/scripts ./scripts

# 前端产物 (从 Stage 1 复制)
COPY --from=frontend-builder /frontend/dist ./static

# 端口
EXPOSE 8000

# 启动
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
