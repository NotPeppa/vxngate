#!/bin/bash
# 快速启动脚本

echo "=== VPN Gate SOCKS5 代理管理系统 ==="
echo ""
echo "正在启动服务..."
docker-compose up -d

echo ""
echo "等待服务启动..."
sleep 5

echo ""
echo "✅ 启动完成！"
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
