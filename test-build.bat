@echo off
REM 测试 Docker 构建脚本 - Windows

echo === 测试 Docker 构建 ===
echo.

echo 1. 测试预编译版 Dockerfile（推荐）...
docker build -f Dockerfile.prebuilt -t vpngate-socks5:test . > build-prebuilt.log 2>&1
if %errorlevel% equ 0 (
    echo ✅ 预编译版 Dockerfile 构建成功
    echo.
    echo 推荐使用此版本：
    echo docker build -f Dockerfile.prebuilt -t vpngate-socks5 .
    docker rmi vpngate-socks5:test
    goto :end
)

echo ❌ 预编译版构建失败，尝试其他版本...
echo.

echo 2. 测试多阶段构建 Dockerfile...
docker build -t vpngate-socks5:test . > build.log 2>&1
if %errorlevel% equ 0 (
    echo ✅ 多阶段构建 Dockerfile 构建成功
    docker rmi vpngate-socks5:test
    goto :end
)

echo ❌ 多阶段构建失败，尝试简化版...
echo.

echo 3. 测试简化版 Dockerfile...
docker build -f Dockerfile.simple -t vpngate-socks5:test . > build-simple.log 2>&1
if %errorlevel% equ 0 (
    echo ✅ 简化版 Dockerfile 构建成功
    echo.
    echo 建议使用：
    echo docker build -f Dockerfile.simple -t vpngate-socks5 .
    docker rmi vpngate-socks5:test
    goto :end
)

echo ❌ 所有版本都构建失败
echo.
echo 请检查：
echo 1. Docker Desktop 是否正常运行
echo 2. 网络连接是否正常
echo 3. 查看日志文件：build-prebuilt.log, build.log, build-simple.log
echo.
echo 或使用预构建镜像：
echo docker pull ghcr.io/your-username/vpngate-socks5:latest

:end
echo.
echo 测试完成
pause
