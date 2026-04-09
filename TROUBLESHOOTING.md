# 故障排查指南

## 问题：没有找到任何服务器

### 可能原因

1. **网络连接问题**
   - 容器无法访问外网
   - VPN Gate API 被屏蔽

2. **VPN Gate API 问题**
   - 服务暂时不可用
   - API 格式变更

3. **容器配置问题**
   - Python 依赖缺失
   - 权限问题

### 排查步骤

#### 1. 检查容器日志

```bash
docker-compose logs -f
```

查找错误信息，特别是：
- `获取服务器列表失败`
- `网络请求失败`
- `解析失败`

#### 2. 测试 API 连接

在浏览器中访问：
```
http://localhost:5000/api/test
```

应该返回类似：
```json
{
  "success": true,
  "status_code": 200,
  "content_length": 123456,
  "first_100_chars": "*vpn_servers\n#HostName,IP,Score..."
}
```

#### 3. 手动测试 VPN Gate API

```bash
# 在容器内测试
docker exec -it vpngate-socks5-web bash
curl https://www.vpngate.net/api/iphone/

# 或在主机测试
curl https://www.vpngate.net/api/iphone/
```

应该返回 CSV 格式的服务器列表。

#### 4. 检查 Python 依赖

```bash
docker exec -it vpngate-socks5-web bash
pip3 list | grep requests
```

应该显示 `requests` 包已安装。

### 解决方案

#### 方案 1：重启容器

```bash
docker-compose down
docker-compose up -d
```

#### 方案 2：检查网络

```bash
# 测试容器网络
docker exec -it vpngate-socks5-web ping -c 3 www.vpngate.net

# 测试 DNS
docker exec -it vpngate-socks5-web nslookup www.vpngate.net
```

#### 方案 3：使用代理

如果 VPN Gate 被屏蔽，配置 HTTP 代理：

编辑 `docker-compose.yml`：
```yaml
services:
  vpngate-socks:
    environment:
      - HTTP_PROXY=http://your-proxy:port
      - HTTPS_PROXY=http://your-proxy:port
```

#### 方案 4：使用备用 API

修改 `web/app.py`，添加备用 API：

```python
# 尝试多个 API 端点
urls = [
    'https://www.vpngate.net/api/iphone/',
    'http://www.vpngate.net/api/iphone/',
]

for url in urls:
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            break
    except:
        continue
```

#### 方案 5：增加超时时间

修改 `web/app.py`：
```python
response = requests.get(url, timeout=30)  # 从 10 秒改为 30 秒
```

### 调试模式

启用详细日志：

```bash
# 查看 Flask 日志
docker-compose logs -f vpngate-socks

# 进入容器查看
docker exec -it vpngate-socks5-web bash
cd /app
python3 app.py
```

### 常见错误信息

#### 错误 1：`requests.exceptions.ConnectionError`

**原因**：无法连接到 VPN Gate API

**解决**：
1. 检查网络连接
2. 检查防火墙设置
3. 尝试使用代理

#### 错误 2：`csv.Error: line contains NULL byte`

**原因**：CSV 数据损坏

**解决**：
1. 重试加载
2. 检查 API 响应内容

#### 错误 3：`KeyError: 'HostName'`

**原因**：CSV 格式变更

**解决**：
1. 查看 API 返回的实际字段
2. 更新代码以匹配新格式

### 获取帮助

如果以上方法都无法解决：

1. 收集以下信息：
   - 容器日志：`docker-compose logs > logs.txt`
   - API 测试结果：访问 `/api/test`
   - 网络测试结果

2. 创建 Issue 并附上信息

3. 临时方案：手动添加服务器
   - 访问 https://www.vpngate.net/
   - 手动复制服务器信息
   - 直接使用 IP 连接

## 其他常见问题

### 连接失败

**症状**：点击连接后无响应或失败

**解决**：
1. 选择其他服务器
2. 检查 SoftEther VPN Client 是否运行
3. 查看容器日志

### SOCKS5 代理无响应

**症状**：连接成功但代理不工作

**解决**：
1. 检查 Dante 是否运行：`docker exec vpngate-socks5-web ps aux | grep danted`
2. 检查虚拟网卡：`docker exec vpngate-socks5-web ip addr show vpn_vpn`
3. 重启 SOCKS5 代理

### Web 界面无法访问

**症状**：无法打开 http://localhost:5000

**解决**：
1. 检查容器是否运行：`docker ps`
2. 检查端口映射：`docker port vpngate-socks5-web`
3. 检查防火墙设置

---

**提示**：大多数问题可以通过查看容器日志快速定位。
