#!/bin/bash
set -e

echo "=== 启动 VPN Gate SOCKS5 代理管理系统 ==="

# 检查 SoftEther VPN Client 是否需要编译
if [ ! -f /opt/vpnclient/vpnclient ]; then
    echo "首次运行，正在编译 SoftEther VPN Client..."
    cd /opt/vpnclient
    (echo "1"; echo "1"; echo "1") | make || true
fi

# 启动 SoftEther VPN Client
echo "启动 SoftEther VPN Client..."
cd /opt/vpnclient
./vpnclient start || true

# 等待 VPN 客户端启动
sleep 3

# 启动 SOCKS5 代理服务器（初始状态，等待连接后会重启）
echo "启动 SOCKS5 代理服务器..."
danted -f /etc/danted.conf &

# 启动 Web 管理界面
echo "启动 Web 管理界面..."
cd /app
python3 app.py &

echo ""
echo "=== 系统启动完成 ==="
echo "Web 管理界面: http://localhost:5000"
echo "SOCKS5 代理: localhost:1080"
echo ""

# 保持容器运行
tail -f /dev/null
