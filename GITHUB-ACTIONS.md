# GitHub Actions 说明

## 工作流程

本项目使用 2 个 GitHub Actions 工作流：

### 1. Docker Build（必需）✅

**文件**: `.github/workflows/docker-build.yml`

**触发条件**:
- 推送到 main/master 分支
- 创建标签 (v*)
- Pull Request
- 手动触发

**功能**:
- 自动构建 Docker 镜像
- 推送到 GitHub Container Registry
- 支持多平台 (amd64, arm64)
- 自动尝试 3 个 Dockerfile 版本

**构建策略**:
1. 首先尝试 `Dockerfile.prebuilt`（最可靠）
2. 失败则尝试 `Dockerfile`（标准版）
3. 还失败则尝试 `Dockerfile.simple`（备用）

### 2. Release（可选）

**文件**: `.github/workflows/release.yml`

**触发条件**:
- 创建标签 (v*)

**功能**:
- 自动创建 GitHub Release
- 生成发布包 (zip, tar.gz)
- 添加发布说明

## 状态说明

### ✅ 成功状态

- **Docker Build 成功** - 镜像已构建并推送
- 可以使用预构建镜像：`ghcr.io/your-username/vpngate-socks5:latest`

### ⚠️ 部分失败

- **某个 Dockerfile 失败** - 没关系，只要有一个成功即可
- 查看日志了解哪个版本成功了

### ❌ 完全失败

- **所有 Dockerfile 都失败** - 需要检查代码
- 查看 Actions 日志排查问题

## 查看构建结果

1. 访问仓库的 `Actions` 标签
2. 点击最新的工作流运行
3. 查看详细日志

## 使用预构建镜像

构建成功后，可以直接使用：

```bash
docker pull ghcr.io/your-username/vpngate-socks5:latest
docker run -d \
  --name vpngate-socks5 \
  --cap-add=NET_ADMIN \
  --device=/dev/net/tun \
  -p 1080:1080 \
  -p 5000:5000 \
  ghcr.io/your-username/vpngate-socks5:latest
```

或修改 `docker-compose.yml`：

```yaml
services:
  vpngate-socks:
    image: ghcr.io/your-username/vpngate-socks5:latest
    # 注释掉 build: .
```

## 权限配置

确保 GitHub Actions 有正确的权限：

1. 访问仓库 `Settings` → `Actions` → `General`
2. 在 "Workflow permissions" 选择：
   - ✅ `Read and write permissions`
3. 勾选：
   - ✅ `Allow GitHub Actions to create and approve pull requests`
4. 点击 `Save`

## 常见问题

### Q: Test Build 失败了怎么办？

A: Test Build 已被移除，不是必需的。只要 Docker Build 成功即可。

### Q: Docker Build 失败了怎么办？

A: 查看日志，通常会自动尝试其他 Dockerfile 版本。如果全部失败，检查：
- 网络连接
- 依赖包是否可用
- Dockerfile 语法

### Q: 如何手动触发构建？

A: 
1. 访问 `Actions` 标签
2. 选择 "Build and Push Docker Image"
3. 点击 "Run workflow"
4. 选择分支并运行

### Q: 镜像在哪里？

A: 
- 访问仓库的 `Packages` 标签
- 或直接访问：`ghcr.io/your-username/vpngate-socks5`

## 禁用 Actions

如果不需要自动构建，可以：

1. 删除 `.github/workflows/` 目录
2. 或在仓库 Settings → Actions 中禁用

## 本地构建

不依赖 GitHub Actions，本地构建：

```bash
# 使用预编译版（推荐）
docker build -f Dockerfile.prebuilt -t vpngate-socks5 .

# 或运行测试脚本
bash test-build.sh  # Linux/Mac
test-build.bat      # Windows
```

---

**总结**: 只要 Docker Build 成功，项目就可以正常使用。其他失败的工作流都是可选的。
