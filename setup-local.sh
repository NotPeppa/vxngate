#!/bin/bash
# VPN Gate SSL-VPN 转 SOCKS5 代理 - 本地安装脚本
# 适用于 Linux 系统

set -e

echo "=== VPN Gate 转 SOCKS5 代理安装脚本 ==="

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 安装依赖
echo "正在安装依赖..."
apt-get update
apt-get install -y wget gcc make libreadline-dev libssl-dev \
    libncurses5-dev zlib1g-dev dante-server iproute2 iptables

# 下载 SoftEther VPN Client
echo "正在下载 SoftEther VPN Client..."
cd /tmp
wget https://github.com/SoftEtherVPN/SoftEtherVPN_Stable/releases/download/v4.43-9799-beta/softether-vpnclient-v4.43-9799-beta-2023.08.31-linux-x64-64bit.tar.gz

# 解压并编译
echo "正在编译 SoftEther VPN Client..."
tar xzf softether-vpnclient-*.tar.gz
cd vpnclient
make i_read_and_agree_the_license_agreement

# 安装到系统目录
echo "正在安装..."
mkdir -p /opt/vpnclient
cp -r * /opt/vpnclient/
cd /opt/vpnclient

# 创建 systemd 服务
cat > /etc/systemd/system/vpnclient.service <<'EOF'
[Unit]
Description=SoftEther VPN Client
After=network.target

[Service]
Type=forking
ExecStart=/opt/vpnclient/vpnclient start
ExecStop=/opt/vpnclient/vpnclient stop
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# 配置 SOCKS5 代理
cat > /etc/danted.conf <<'EOF'
logoutput: syslog

internal: 0.0.0.0 port = 1080
external: vpn_vpn

clientmethod: none
socksmethod: none

client pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
}

socks pass {
    from: 0.0.0.0/0 to: 0.0.0.0/0
    log: error
}
EOF

# 创建 SOCKS5 服务
cat > /etc/systemd/system/danted-vpn.service <<'EOF'
[Unit]
Description=Dante SOCKS5 Proxy for VPN
After=vpnclient.service
Requires=vpnclient.service

[Service]
Type=simple
ExecStart=/usr/sbin/danted -f /etc/danted.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# 重载 systemd
systemctl daemon-reload

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方法："
echo "1. 启动 VPN 客户端："
echo "   sudo systemctl start vpnclient"
echo ""
echo "2. 配置 VPN 连接（替换为实际的服务器信息）："
echo "   cd /opt/vpnclient"
echo "   sudo ./vpncmd localhost /CLIENT /CMD NicCreate vpn"
echo "   sudo ./vpncmd localhost /CLIENT /CMD AccountCreate vpngate /SERVER:219.100.37.55:443 /HUB:VPNGATE /USERNAME:vpn /NICNAME:vpn"
echo "   sudo ./vpncmd localhost /CLIENT /CMD AccountPasswordSet vpngate /PASSWORD:vpn /TYPE:standard"
echo "   sudo ./vpncmd localhost /CLIENT /CMD AccountConnect vpngate"
echo ""
echo "3. 配置虚拟网卡："
echo "   sudo dhclient vpn_vpn"
echo ""
echo "4. 启动 SOCKS5 代理："
echo "   sudo systemctl start danted-vpn"
echo ""
echo "5. 测试连接："
echo "   curl --socks5 localhost:1080 ifconfig.me"
echo ""
echo "设置开机自启："
echo "   sudo systemctl enable vpnclient"
echo "   sudo systemctl enable danted-vpn"
