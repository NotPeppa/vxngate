#!/bin/bash
# 测试 Docker 构建脚本

echo "=== 测试 Docker 构建 ==="
echo ""

# 测试预编译版（最可靠）
echo "1. 测试预编译版 Dockerfile（推荐）..."
if docker build -f Dockerfile.prebuilt -t vpngate-socks5:test . 2>&1 | tee build-prebuilt.log; then
    echo "✅ 预编译版 Dockerfile 构建成功"
    echo ""
    echo "推荐使用此版本："
    echo "docker build -f Dockerfile.prebuilt -t vpngate-socks5 ."
    docker rmi vpngate-socks5:test
    exit 0
fi

echo "❌ 预编译版构建失败，尝试其他版本..."
echo ""

# 测试主 Dockerfile
echo "2. 测试多阶段构建 Dockerfile..."
if docker build -t vpngate-socks5:test . 2>&1 | tee build.log; then
    echo "✅ 多阶段构建 Dockerfile 构建成功"
    docker rmi vpngate-socks5:test
    exit 0
fi

echo "❌ 多阶段构建失败，尝试简化版..."
echo ""

# 测试简化版
echo "3. 测试简化版 Dockerfile..."
if docker build -f Dockerfile.simple -t vpngate-socks5:test . 2>&1 | tee build-simple.log; then
    echo "✅ 简化版 Dockerfile 构建成功"
    echo ""
    echo "建议使用："
    echo "docker build -f Dockerfile.simple -t vpngate-socks5 ."
    docker rmi vpngate-socks5:test
    exit 0
fi

echo "❌ 所有版本都构建失败"
echo ""
echo "请检查："
echo "1. Docker 是否正常运行"
echo "2. 网络连接是否正常"
echo "3. 查看日志文件：build-prebuilt.log, build.log, build-simple.log"
echo ""
echo "或使用预构建镜像："
echo "docker pull ghcr.io/your-username/vpngate-socks5:latest"

exit 1
