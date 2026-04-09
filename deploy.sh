#!/bin/bash
# 一键部署脚本

set -e

echo "=== VPN Gate SOCKS5 代理管理系统 - 部署脚本 ==="
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker 和 Docker Compose 已安装"
echo ""

# 停止旧容器
echo "停止旧容器..."
docker-compose down 2>/dev/null || true

# 拉取最新镜像（如果使用预构建镜像）
if grep -q "image:" docker-compose.yml; then
    echo "拉取最新镜像..."
    docker-compose pull
fi

# 构建镜像（如果使用本地构建）
if grep -q "build:" docker-compose.yml; then
    echo "构建 Docker 镜像..."
    docker-compose build --no-cache
fi

# 启动服务
echo "启动服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 5

# 检查服务状态
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ 部署成功！"
    echo ""
    echo "📱 Web 管理界面: http://localhost:5000"
    echo "🔌 SOCKS5 代理: localhost:1080"
    echo ""
    echo "使用方法："
    echo "1. 在浏览器中打开 http://localhost:5000"
    echo "2. 选择一个服务器并点击"连接""
    echo "3. 配置你的应用使用 SOCKS5 代理 localhost:1080"
    echo ""
    echo "查看日志: docker-compose logs -f"
    echo "停止服务: docker-compose down"
else
    echo ""
    echo "❌ 部署失败"
    echo "查看日志: docker-compose logs"
    exit 1
fi
