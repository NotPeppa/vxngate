@echo off
REM 一键部署脚本 - Windows

echo === VPN Gate SOCKS5 代理管理系统 - 部署脚本 ===
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: Docker 未安装
    echo 请先安装 Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: Docker Compose 未安装
    echo Docker Desktop 应该已包含 Docker Compose
    pause
    exit /b 1
)

echo ✅ Docker 和 Docker Compose 已安装
echo.

REM 停止旧容器
echo 停止旧容器...
docker-compose down 2>nul

REM 拉取最新镜像（如果使用预构建镜像）
findstr /C:"image:" docker-compose.yml >nul
if not errorlevel 1 (
    echo 拉取最新镜像...
    docker-compose pull
)

REM 构建镜像（如果使用本地构建）
findstr /C:"build:" docker-compose.yml >nul
if not errorlevel 1 (
    echo 构建 Docker 镜像...
    docker-compose build --no-cache
)

REM 启动服务
echo 启动服务...
docker-compose up -d

REM 等待服务启动
echo 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
docker-compose ps | findstr "Up" >nul
if not errorlevel 1 (
    echo.
    echo ✅ 部署成功！
    echo.
    echo 📱 Web 管理界面: http://localhost:5000
    echo 🔌 SOCKS5 代理: localhost:1080
    echo.
    echo 使用方法：
    echo 1. 在浏览器中打开 http://localhost:5000
    echo 2. 选择一个服务器并点击"连接"
    echo 3. 配置你的应用使用 SOCKS5 代理 localhost:1080
    echo.
    echo 查看日志: docker-compose logs -f
    echo 停止服务: docker-compose down
    echo.
    
    REM 自动打开浏览器
    start http://localhost:5000
) else (
    echo.
    echo ❌ 部署失败
    echo 查看日志: docker-compose logs
    pause
    exit /b 1
)

pause
