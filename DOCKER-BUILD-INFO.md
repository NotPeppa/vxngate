# Docker 构建说明

## 🎯 构建策略

本项目提供 3 个 Dockerfile，按优先级自动尝试：

### 1. Dockerfile.prebuilt（首选）
- **最可靠**：不需要编译
- **最快速**：直接使用预编译二进制
- **推荐使用**

### 2. Dockerfile（标准）
- 多阶段构建
- 镜像体积小
- 适合生产环境

### 3. Dockerfile.simple（备用）
- 单阶段构建
- 最简单
- 镜像较大

## 🚀 本地构建

### 快速开始
```bash
# 推荐：使用预编译版
docker build -f Dockerfile.prebuilt -t vpngate-socks5 .

# 或使用 docker-compose
docker-compose up -d
```

### 测试所有版本
```bash
# Windows
test-build.bat

# Linux/Mac
bash test-build.sh
```

## 🤖 GitHub Actions

GitHub Actions 会自动：
1. 尝试 Dockerfile.prebuilt
2. 如果失败，尝试 Dockerfile
3. 如果还失败，尝试 Dockerfile.simple
4. 至少有一个成功即可

## 📦 使用预构建镜像

```bash
docker pull ghcr.io/your-username/vpngate-socks5:latest
```

## ❓ 常见问题

**Q: 为什么有 3 个 Dockerfile？**
A: 不同环境可能需要不同的构建方式，提供多个选择确保至少有一个能成功。

**Q: 应该使用哪个？**
A: 优先使用 Dockerfile.prebuilt，它最可靠。

**Q: 构建失败怎么办？**
A: 运行测试脚本或查看 [BUILD-GUIDE.md](BUILD-GUIDE.md)
