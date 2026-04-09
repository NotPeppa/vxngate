@echo off
REM 测试 Docker 构建脚本 - Windows

echo === 测试 Docker 构建 ===
echo.

echo 1. 测试主 Dockerfile...
docker build -t vpngate-socks5:test . > build.log 2>&1
if %errorlevel% equ 0 (
    echo ✅ 主 Dockerfile 构建成功
    docker rmi vpngate-socks5:test
) else (
    echo ❌ 主 Dockerfile 构建失败
    echo.
    echo 2. 尝试简化版 Dockerfile...
    docker build -f Dockerfile.simple -t vpngate-socks5:test . > build-simple.log 2>&1
    if %errorlevel% equ 0 (
        echo ✅ 简化版 Dockerfile 构建成功
        echo.
        echo 建议：使用 Dockerfile.simple 进行构建
        echo 命令：docker build -f Dockerfile.simple -t vpngate-socks5 .
        docker rmi vpngate-socks5:test
    ) else (
        echo ❌ 简化版 Dockerfile 也构建失败
        echo.
        echo 请检查：
        echo 1. Docker Desktop 是否正常运行
        echo 2. 网络连接是否正常
        echo 3. 查看日志文件：build.log 和 build-simple.log
    )
)

echo.
echo 测试完成
pause
