# Windows 用户指南

在 Windows 上使用 VPN Gate SOCKS5 代理管理系统。

## 🚀 快速开始

### 1. 安装 Docker Desktop

下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)

### 2. 启动服务

双击运行 `start.bat`，浏览器会自动打开 http://localhost:5000

### 3. 连接服务器

在 Web 界面选择服务器并点击"连接"

就这么简单！

## 📱 配置浏览器

### Firefox
1. 设置 → 网络设置 → 手动代理配置
2. SOCKS Host: `localhost`, Port: `1080`
3. 选择 SOCKS v5

### Chrome/Edge
安装 [Proxy SwitchyOmega](https://chrome.google.com/webstore/detail/proxy-switchyomega/) 扩展
- 协议：SOCKS5
- 服务器：localhost
- 端口：1080

## 🧪 测试连接

```powershell
curl --socks5 localhost:1080 ifconfig.me
```

## ❓ 常见问题

**Q: Docker Desktop 无法启动？**
- 确保已启用 WSL2
- 检查 Windows 版本（需要 Windows 10 1903+ 或 Windows 11）

**Q: 连接失败？**
- 在 Web 界面尝试其他服务器
- 选择速度高、延迟低的服务器

**Q: 速度慢？**
- 选择地理位置近的服务器
- 选择推荐分数高的服务器

## 📚 更多帮助

- [主文档](README.md)
- [贡献指南](CONTRIBUTING.md)
