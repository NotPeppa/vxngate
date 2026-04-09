# SoftEther VPN Client + SOCKS5 Proxy + Web 管理界面
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装依赖
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    dante-server \
    iproute2 \
    iptables \
    dhcpcd5 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 下载 SoftEther VPN Client（使用最新稳定版）
WORKDIR /tmp
RUN wget -q --show-progress \
    https://github.com/SoftEtherVPN/SoftEtherVPN_Stable/releases/download/v4.43-9799-beta/softether-vpnclient-v4.43-9799-beta-2023.08.31-linux-x64-64bit.tar.gz \
    && tar xzf softether-vpnclient-*.tar.gz \
    && mkdir -p /opt/vpnclient \
    && cp -r vpnclient/* /opt/vpnclient/ \
    && rm -rf /tmp/*

# 编译 SoftEther VPN Client
WORKDIR /opt/vpnclient
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    libreadline-dev \
    libssl-dev \
    libncurses5-dev \
    zlib1g-dev \
    && yes 1 | make \
    && apt-get purge -y gcc make libreadline-dev libssl-dev libncurses5-dev zlib1g-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

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

EXPOSE 1080 5000

CMD ["/entrypoint.sh"]
