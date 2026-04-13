#!/bin/bash
set -e

echo "=== 启动 VPN Gate SOCKS5 代理管理系统 ==="

# 读取认证配置（可通过环境变量覆盖）
SOCKS_USERNAME="${SOCKS_USERNAME:-socks}"
SOCKS_PASSWORD="${SOCKS_PASSWORD:-change_me_now}"
WEB_USERNAME="${WEB_USERNAME:-admin}"
WEB_PASSWORD="${WEB_PASSWORD:-admin_change_me}"

export WEB_USERNAME
export WEB_PASSWORD

echo "配置 SOCKS5 认证用户: ${SOCKS_USERNAME}"
echo "配置 Web 管理用户: ${WEB_USERNAME}"

# 尝试准备 TUN 设备（部分环境不会自动挂载 /dev/net/tun）
if [ ! -c /dev/net/tun ]; then
    mkdir -p /dev/net || true
    mknod /dev/net/tun c 10 200 2>/dev/null || true
    chmod 666 /dev/net/tun 2>/dev/null || true
fi

if [ -c /dev/net/tun ]; then
    echo "TUN 设备已就绪: /dev/net/tun"
else
    echo "警告: 未检测到 /dev/net/tun，VPN 连接功能将不可用"
fi

# 创建/更新 SOCKS5 系统用户（供 danted 的 username 认证使用）
if ! id -u "${SOCKS_USERNAME}" > /dev/null 2>&1; then
    useradd -M -s /usr/sbin/nologin "${SOCKS_USERNAME}"
fi
echo "${SOCKS_USERNAME}:${SOCKS_PASSWORD}" | chpasswd

# 生成 danted 配置（启用用户名密码认证）
cat > /etc/danted.conf <<EOF
logoutput: stderr

internal: 0.0.0.0 port = 1080
external: vpn_vpn

clientmethod: none
socksmethod: username

user.privileged: root
user.unprivileged: nobody

client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
}

socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    socksmethod: username
    log: error
}
EOF

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

# 启动 SOCKS5 代理服务器（等待 VPN 连接后由 Web API 启动）
echo "等待 VPN 连接后启动 SOCKS5 代理服务器..."

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
