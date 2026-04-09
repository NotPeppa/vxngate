# 贡献指南

感谢你考虑为 VPN Gate SOCKS5 代理管理系统做出贡献！

## 如何贡献

### 报告 Bug

如果你发现了 bug，请创建一个 Issue，并包含以下信息：

1. **Bug 描述**：清晰简洁地描述问题
2. **重现步骤**：详细的重现步骤
3. **期望行为**：你期望发生什么
4. **实际行为**：实际发生了什么
5. **环境信息**：
   - 操作系统和版本
   - Docker 版本
   - 浏览器版本（如果相关）
6. **日志**：相关的错误日志或截图

### 提出新功能

如果你有新功能的想法：

1. 先检查 Issue 列表，确保没有重复
2. 创建一个 Feature Request Issue
3. 详细描述功能和使用场景
4. 说明为什么这个功能有用

### 提交代码

#### 开发流程

1. **Fork 仓库**
   ```bash
   # 在 GitHub 上点击 Fork 按钮
   ```

2. **克隆你的 Fork**
   ```bash
   git clone https://github.com/your-username/vpngate-socks5.git
   cd vpngate-socks5
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

4. **进行修改**
   - 遵循代码风格
   - 添加必要的注释
   - 更新相关文档

5. **测试修改**
   ```bash
   # 构建 Docker 镜像
   docker build -t vpngate-socks5:test .
   
   # 测试运行
   docker-compose up -d
   
   # 测试功能
   # 访问 http://localhost:5000
   # 测试连接、切换等功能
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   # 或
   git commit -m "fix: 修复某个问题"
   ```

7. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待审核

#### 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)：**
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

**示例：**
```
feat(web): 添加服务器收藏功能

- 添加收藏按钮
- 实现收藏列表
- 持久化收藏数据

Closes #123
```

### 代码风格

#### Python (Flask 后端)

- 遵循 PEP 8
- 使用 4 个空格缩进
- 函数和变量使用 snake_case
- 类使用 PascalCase
- 添加类型提示（Python 3.6+）

```python
def get_vpngate_servers() -> list[dict]:
    """获取 VPN Gate 服务器列表
    
    Returns:
        list[dict]: 服务器信息列表
    """
    pass
```

#### JavaScript (前端)

- 使用 2 个空格缩进
- 使用 camelCase 命名
- 添加注释说明复杂逻辑

```javascript
async function loadServers() {
    // 从 API 获取服务器列表
    const response = await fetch('/api/servers');
    const data = await response.json();
    return data.servers;
}
```

#### HTML/CSS

- 使用 2 个空格缩进
- 语义化 HTML 标签
- CSS 类名使用 kebab-case

```html
<div class="server-card">
    <h3 class="server-name">Japan</h3>
</div>
```

### 文档

- 更新相关的 Markdown 文档
- 保持文档与代码同步
- 使用清晰的中文或英文
- 添加代码示例

### 测试

虽然目前没有自动化测试，但请确保：

1. 手动测试所有修改的功能
2. 测试不同的浏览器（Chrome、Firefox、Safari）
3. 测试不同的操作系统（Windows、Linux、Mac）
4. 确保 Docker 镜像能正常构建和运行

### Pull Request 检查清单

在提交 PR 之前，请确认：

- [ ] 代码遵循项目的代码风格
- [ ] 已添加必要的注释
- [ ] 已更新相关文档
- [ ] 已手动测试所有修改
- [ ] 提交信息遵循规范
- [ ] PR 描述清晰，说明了修改内容
- [ ] 没有引入新的警告或错误
- [ ] Docker 镜像能正常构建

## 开发环境设置

### 本地开发

1. **安装依赖**
   ```bash
   # Python 依赖
   pip install -r web/requirements.txt
   
   # 或使用虚拟环境
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   pip install -r web/requirements.txt
   ```

2. **运行 Flask 应用**
   ```bash
   cd web
   python app.py
   ```

3. **访问界面**
   ```
   http://localhost:5000
   ```

### Docker 开发

```bash
# 构建镜像
docker build -t vpngate-socks5:dev .

# 运行容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 进入容器
docker exec -it vpngate-socks5-web bash
```

## 项目结构

```
vpngate-socks5/
├── web/                    # Web 应用
│   ├── app.py             # Flask 后端
│   ├── templates/         # HTML 模板
│   └── requirements.txt   # Python 依赖
├── Dockerfile             # Docker 镜像
├── docker-compose.yml     # Docker Compose 配置
├── danted.conf           # SOCKS5 配置
└── docs/                 # 文档
```

## 获取帮助

如果你有任何问题：

1. 查看 [文档](README.md)
2. 搜索 [Issues](https://github.com/yourusername/vpngate-socks5/issues)
3. 创建新的 Issue 提问

## 行为准则

### 我们的承诺

为了营造一个开放和友好的环境，我们承诺：

- 使用友好和包容的语言
- 尊重不同的观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

### 不可接受的行为

- 使用性化的语言或图像
- 人身攻击或侮辱性评论
- 公开或私下的骚扰
- 未经许可发布他人的私人信息
- 其他不道德或不专业的行为

## 许可证

通过贡献代码，你同意你的贡献将在 [MIT License](LICENSE) 下授权。

---

再次感谢你的贡献！🎉
