# 构建指南

## 构建问题排查

如果遇到 Docker 构建失败，按以下步骤排查：

### 1. 测试构建

**Windows:**
```bash
test-build.bat
```

**Linux/Mac:**
```bash
bash test-build.sh
```

### 2. 常见问题

#### 问题：SoftEther VPN 编译失败

**错误信息：**
```
make i_read_and_agree_the_license_agreement
exit code: 2
```

**解决方案：**

**方法 1：使用简化版 Dockerfile**
```bash
docker build -f Dockerfile.simple -t vpngate-socks5 .
```

**方法 2：使用预构建镜像**
```bash
# 修改 docker-compose.yml
services:
  vpngate-socks:
    image: ghcr.io/your-username/vpngate-socks5:latest
    # 注释掉 build: .
```

#### 问题：网络超时

**错误信息：**
```
wget: unable to resolve host address
```

**解决方案：**
1. 检查网络连接
2. 配置 Docker 代理
3. 使用国内镜像源

#### 问题：依赖安装失败

**错误信息：**
```
E: Unable to locate package
```

**解决方案：**
```bash
# 清理 Docker 缓存
docker builder prune -a

# 重新构建
docker build --no-cache -t vpngate-socks5 .
```

### 3. Dockerfile 版本说明

#### Dockerfile（标准版）
- 下载 SoftEther VPN 源码
- 编译并安装
- 清理编译工具以减小镜像大小
- 推荐用于生产环境

#### Dockerfile.simple（简化版）
- 保留所有编译工具
- 构建步骤更简单
- 镜像体积较大
- 推荐用于测试和开发

### 4. 手动构建步骤

如果自动构建失败，可以手动构建：

```bash
# 1. 构建基础镜像
docker build -t vpngate-base -f - . << 'EOF'
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    wget ca-certificates gcc make \
    libreadline-dev libssl-dev libncurses5-dev zlib1g-dev \
    dante-server iproute2 iptables dhcpcd5 \
    python3 python3-pip
EOF

# 2. 下载 SoftEther VPN
docker run --rm -v $(pwd):/work -w /work vpngate-base \
    wget https://github.com/SoftEtherVPN/SoftEtherVPN_Stable/releases/download/v4.43-9799-beta/softether-vpnclient-v4.43-9799-beta-2023.08.31-linux-x64-64bit.tar.gz

# 3. 继续构建
docker build -t vpngate-socks5 .
```

### 5. 使用预构建镜像

最简单的方法是使用 GitHub Actions 自动构建的镜像：

```bash
docker pull ghcr.io/your-username/vpngate-socks5:latest
docker-compose up -d
```

### 6. 验证构建

构建成功后，验证镜像：

```bash
# 查看镜像
docker images | grep vpngate-socks5

# 测试运行
docker run --rm vpngate-socks5 /opt/vpnclient/vpncmd --help

# 完整测试
docker-compose up -d
curl http://localhost:5000
```

## 构建优化

### 减小镜像大小

1. 使用多阶段构建
2. 清理 apt 缓存
3. 删除编译工具
4. 压缩层

### 加速构建

1. 使用构建缓存
2. 配置镜像源
3. 并行下载
4. 使用 BuildKit

```bash
# 启用 BuildKit
export DOCKER_BUILDKIT=1
docker build -t vpngate-socks5 .
```

## 获取帮助

如果仍然无法构建：

1. 查看构建日志：`build.log`
2. 创建 Issue 并附上日志
3. 使用预构建镜像作为临时方案

---

**提示：** 大多数用户可以直接使用预构建镜像，无需自己构建。
