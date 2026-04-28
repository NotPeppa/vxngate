# SoftEther VPN Client + SOCKS5 Proxy + Web 管理界面
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# 安装编译依赖
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    gcc \
    make \
    libreadline-dev \
    libssl-dev \
    libncurses5-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 下载并编译 SoftEther VPN Client
WORKDIR /build
RUN set -eux; \
    url="https://github.com/SoftEtherVPN/SoftEtherVPN_Stable/releases/download/v4.43-9799-beta/softether-vpnclient-v4.43-9799-beta-2023.08.31-linux-x64-64bit.tar.gz"; \
    wget --https-only --tries=5 --waitretry=3 --retry-connrefused --timeout=30 -O softether-vpnclient.tar.gz "$url"; \
    tar xzf softether-vpnclient.tar.gz; \
    rm softether-vpnclient.tar.gz; \
    cd vpnclient; \
    echo "1\n1\n1" | make

# 最终镜像
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    dante-server \
    openvpn \
    iproute2 \
    iptables \
    dhcpcd5 \
    udhcpc \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制编译好的 SoftEther VPN Client
COPY --from=builder /build/vpnclient /opt/vpnclient

# 安装 Python 依赖
COPY web/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# 复制 Web 应用
COPY web /app

# 复制启动脚本和配置
COPY entrypoint-web.sh /entrypoint.sh
COPY danted.conf /etc/danted.conf
RUN chmod +x /entrypoint.sh

# 创建配置目录
RUN mkdir -p /config

WORKDIR /opt/vpnclient

EXPOSE 1080 5000

CMD ["/entrypoint.sh"]
