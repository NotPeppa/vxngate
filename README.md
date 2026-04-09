# 🚀 VPN Gate SOCKS5 代理管理系统

> 将 VPN Gate 的 SSL-VPN 转换为 SOCKS5 代理，带美观的 Web 管理界面

[![Docker Build](https://github.com/your-username/vpngate-socks5/actions/workflows/docker-build.yml/badge.svg)](https://github.com/your-username/vpngate-socks5/actions/workflows/docker-build.yml)
[![License](https://img.shields.io/github/license/your-username/vpngate-socks5)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/your-username/vpngate-socks5)](https://github.com/your-username/vpngate-socks5/releases)

## ✨ 特性

- 🌐 **自动获取服务器** - 从 VPN Gate 自动获取最新服务器列表
- 🖥️ **Web 管理界面** - 美观的现代化界面，一键操作
- 🔄 **快速切换** - 无需重启容器，秒级切换服务器
- 📊 **实时信息** - 显示速度、延迟、国家等详细信息
- 🔍 **智能筛选** - 按国家、速度、延迟等条件筛选
- 🎯 **一键连接** - 点击即连，自动配置 SOCKS5 代理
- 🐳 **容器化** - Docker 部署，跨平台支持
- 🔒 **SSL-VPN** - 支持 VPN Gate 覆盖率最高的协议

## 🚀 快速开始

### 方式 1：一键启动（推荐）

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
bash start.sh
```

### 方式 2：Docker Compose

```bash
# 启动服务
docker-compose up -d

# 打开浏览器访问
http://localhost:5000
```

### 方式 3：使用预构建镜像

```bash
docker pull ghcr.io/your-username/vpngate-socks5:latest
docker-compose up -d
```

就这么简单！打开 http://localhost:5000，选择服务器并连接。

## 📱 使用说明

1. **打开 Web 界面**: http://localhost:5000
2. **浏览服务器列表**: 自动显示 VPN Gate 服务器
3. **筛选服务器**: 按国家、速度、延迟筛选
4. **点击连接**: 一键连接到选中的服务器
5. **使用代理**: 配置应用使用 `localhost:1080` SOCKS5 代理

## 功能特点

- ✅ 支持 VPN Gate 的 SSL-VPN 协议（覆盖率最高）
- ✅ 自动获取 VPN Gate 服务器列表
- ✅ Web 界面一键切换服务器
- ✅ 实时显示连接状态
- ✅ 服务器筛选和排序
- ✅ 自动转换为 SOCKS5 代理
- ✅ Docker 容器化部署，简单易用

## 快速开始

### 1. 启动服务

```bash
docker-compose up -d
```

### 2. 打开 Web 管理界面

在浏览器中访问：**http://localhost:5000**

### 3. 选择并连接服务器

- 在 Web 界面中浏览服务器列表
- 可以按国家、速度、延迟等筛选
- 点击"连接"按钮即可一键连接
- SOCKS5 代理自动启动在 `localhost:1080`

## Web 管理界面功能

### 服务器列表
- 自动从 VPN Gate 获取最新服务器列表
- 显示国家、速度、延迟、在线时长等信息
- 实时显示推荐分数

### 筛选和排序
- 按国家名称搜索
- 按速度、延迟、在线时长、推荐分数排序
- 设置最小速度要求

### 连接管理
- 一键连接/断开
- 实时显示连接状态
- 自动配置 SOCKS5 代理

### 界面预览
```
┌─────────────────────────────────────────┐
│  🚀 VPN Gate SOCKS5 代理管理            │
│  ● 已连接: 219.100.37.55                │
│  SOCKS5: localhost:1080                 │
│  [🔄 刷新] [❌ 断开连接]                │
├─────────────────────────────────────────┤
│  搜索: [Japan___] 排序: [推荐分数▼]    │
├─────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐    │
│  │ 🇯🇵 Japan    │  │ 🇺🇸 USA      │    │
│  │ 速度: 384Mbps│  │ 速度: 275Mbps│    │
│  │ 延迟: 15ms   │  │ 延迟: 2ms    │    │
│  │ [连接]       │  │ [连接]       │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
```

### 浏览器配置

#### Firefox
1. 设置 → 网络设置 → 手动代理配置
2. SOCKS Host: `localhost`, Port: `1080`
3. 选择 SOCKS v5

#### Chrome/Edge
使用启动参数：
```bash
chrome --proxy-server="socks5://localhost:1080"
```

### 命令行工具

#### curl
```bash
curl --socks5 localhost:1080 https://example.com
```

#### wget
```bash
wget -e use_proxy=yes -e socks_proxy=127.0.0.1:1080 https://example.com
```

#### git
```bash
git config --global http.proxy socks5://localhost:1080
git config --global https.proxy socks5://localhost:1080
```

## 使用 SOCKS5 代理

连接成功后，SOCKS5 代理会自动在 `localhost:1080` 启动。

## 查看日志

```bash
# 查看容器日志
docker-compose logs -f

# 或
docker logs -f vpngate-socks5-web
```

## 停止服务

```bash
docker-compose down
```

## 管理和维护

### 访问 Web 界面
在浏览器中打开：`http://localhost:5000`

### 切换服务器
直接在 Web 界面中点击其他服务器的"连接"按钮即可自动切换，无需重启容器！

### 更改端口
编辑 `docker-compose.yml`：
```yaml
ports:
  - "8080:1080"  # SOCKS5 端口
  - "8000:5000"  # Web 界面端口
```

## 故障排除

### Docker 构建失败

如果遇到 SoftEther VPN 编译错误，按顺序尝试：

**方法 1：使用预编译版（最可靠）**
```bash
docker build -f Dockerfile.prebuilt -t vpngate-socks5 .
docker-compose up -d
```

**方法 2：使用简化版**
```bash
docker build -f Dockerfile.simple -t vpngate-socks5 .
docker-compose up -d
```

**方法 3：使用预构建镜像**
```bash
# 修改 docker-compose.yml，将 build: . 改为：
# image: ghcr.io/your-username/vpngate-socks5:latest
docker-compose up -d
```

详细说明请查看 [BUILD-GUIDE.md](BUILD-GUIDE.md)

### Web 界面无法访问
- 确认容器正在运行：`docker ps`
- 检查端口是否被占用
- 查看日志：`docker-compose logs -f`

### 连接失败
- 在 Web 界面尝试其他服务器
- 选择速度高、延迟低的服务器
- 检查防火墙设置

### 无法访问网络
- 检查容器日志：`docker logs vpngate-socks5-web`
- 确认 VPN 连接已建立（Web 界面显示"已连接"）
- 测试 SOCKS5 代理：`curl --socks5 localhost:1080 ifconfig.me`

## 高级配置

### 远程访问 Web 界面
如果需要从其他设备访问 Web 界面，修改 `docker-compose.yml`：
```yaml
ports:
  - "0.0.0.0:5000:5000"  # 允许外部访问
```

⚠️ 注意：这会将管理界面暴露到网络，建议仅在可信网络中使用。

### 持久化配置
配置文件保存在 `./config` 目录，包含当前连接信息。删除此目录可重置配置。

### 添加 SOCKS5 认证

编辑 `danted.conf`，修改认证方法（需要重新构建镜像）。

## 系统要求

- Docker 20.10+
- Docker Compose 1.29+
- Linux 内核支持 TUN/TAP

## 🐳 使用预构建镜像

如果不想自己构建，可以直接使用 GitHub Container Registry 的镜像：

```bash
# 拉取镜像
docker pull ghcr.io/your-username/vpngate-socks5:latest

# 运行
docker run -d \
  --name vpngate-socks5 \
  --cap-add=NET_ADMIN \
  --device=/dev/net/tun \
  -p 1080:1080 \
  -p 5000:5000 \
  ghcr.io/your-username/vpngate-socks5:latest
```

或修改 `docker-compose.yml` 使用预构建镜像：
```yaml
services:
  vpngate-socks:
    image: ghcr.io/your-username/vpngate-socks5:latest
    # ... 其他配置保持不变
```

## 📖 更多文档

- [Windows 用户指南](README-Windows.md)
- [故障排查指南](TROUBLESHOOTING.md) ⭐
- [Docker 构建说明](DOCKER-BUILD-INFO.md)
- [构建问题排查](BUILD-GUIDE.md)
- [贡献指南](CONTRIBUTING.md)
- [更新日志](CHANGELOG.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！请查看 [贡献指南](CONTRIBUTING.md)。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
