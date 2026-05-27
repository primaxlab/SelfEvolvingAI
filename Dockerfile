FROM python:3.11-slim

WORKDIR /app

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p .evolution

# 暴露端口
EXPOSE 8000

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 启动
CMD ["python", "api_server.py", "--host", "0.0.0.0", "--port", "8000"]
