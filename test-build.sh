#!/bin/bash
# 测试 Docker 构建脚本

echo "=== 测试 Docker 构建 ==="
echo ""

# 测试主 Dockerfile
echo "1. 测试主 Dockerfile..."
if docker build -t vpngate-socks5:test . 2>&1 | tee build.log; then
    echo "✅ 主 Dockerfile 构建成功"
    docker rmi vpngate-socks5:test
else
    echo "❌ 主 Dockerfile 构建失败"
    echo ""
    echo "2. 尝试简化版 Dockerfile..."
    if docker build -f Dockerfile.simple -t vpngate-socks5:test . 2>&1 | tee build-simple.log; then
        echo "✅ 简化版 Dockerfile 构建成功"
        echo ""
        echo "建议：使用 Dockerfile.simple 进行构建"
        echo "命令：docker build -f Dockerfile.simple -t vpngate-socks5 ."
        docker rmi vpngate-socks5:test
    else
        echo "❌ 简化版 Dockerfile 也构建失败"
        echo ""
        echo "请检查："
        echo "1. Docker 是否正常运行"
        echo "2. 网络连接是否正常"
        echo "3. 查看日志文件：build.log 和 build-simple.log"
    fi
fi

echo ""
echo "测试完成"
