#!/bin/bash
set -e

# 启动 SoftEther VPN Client
cd /opt/vpnclient
./vpnclient start

# 等待 VPN 客户端启动
sleep 3

# 如果提供了 VPN 配置，则连接
if [ -n "$VPN_HOST" ] && [ -n "$VPN_PORT" ]; then
    echo "配置 VPN 连接..."
    
    # 使用 vpncmd 配置连接
    ./vpncmd localhost /CLIENT /CMD NicCreate vpn
    ./vpncmd localhost /CLIENT /CMD AccountCreate vpngate /SERVER:${VPN_HOST}:${VPN_PORT} /HUB:VPNGATE /USERNAME:vpn /NICNAME:vpn
    
    # 如果提供了密码，设置密码
    if [ -n "$VPN_PASSWORD" ]; then
        ./vpncmd localhost /CLIENT /CMD AccountPasswordSet vpngate /PASSWORD:${VPN_PASSWORD} /TYPE:standard
    else
        ./vpncmd localhost /CLIENT /CMD AccountPasswordSet vpngate /PASSWORD:vpn /TYPE:standard
    fi
    
    # 连接到 VPN
    ./vpncmd localhost /CLIENT /CMD AccountConnect vpngate
    
    # 等待连接建立
    sleep 5
    
    # 配置虚拟网卡
    dhclient vpn_vpn || true
fi

# 启动 SOCKS5 代理服务器
echo "启动 SOCKS5 代理服务器..."
danted -f /etc/danted.conf

# 保持容器运行
tail -f /dev/null
