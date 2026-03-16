# 多阶段 Dockerfile，支持灵活使用
# 使用方法：
#   1. 只安装依赖：docker build --target=dependencies -t agent-service:deps .
#   2. 完整构建（含代码）：docker build -t agent-service .
#   3. 运行容器：docker run -d -p 8001:8001 agent-service

# ==================== 阶段 1: 依赖安装 ====================
FROM python:3.11-slim AS dependencies

WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（这一层会被缓存）
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright Chromium，供热点爬虫脚本使用
RUN python -m playwright install --with-deps chromium

# ==================== 阶段 2: 开发环境 ====================
FROM dependencies AS development

# 复制应用代码
COPY app ./app
COPY scripts ./scripts

# 创建必要目录
RUN mkdir -p /app/data /app/logs

# 暴露端口
EXPOSE 8001

# 启动命令（开发模式，带热重载）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# ==================== 阶段 3: 生产环境 ====================
FROM dependencies AS production

# 设置时区为北京时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制应用代码
COPY app ./app
COPY scripts ./scripts

# 创建必要目录
RUN mkdir -p /app/data /app/logs

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /ms-playwright
USER appuser

# 暴露端口
EXPOSE 8001

# 启动命令（生产模式，不带重载）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
