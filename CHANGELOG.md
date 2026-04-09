# 更新日志

所有重要的项目更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划功能
- 服务器收藏功能
- 连接历史记录
- 自动选择最佳服务器
- 速度测试功能
- 流量统计
- 多语言支持

## [1.0.0] - 2024-01-XX

### 新增
- 🎉 首次发布
- ✅ Web 管理界面
- ✅ 自动获取 VPN Gate 服务器列表
- ✅ 一键连接/断开功能
- ✅ 服务器筛选和排序
- ✅ 实时连接状态显示
- ✅ SOCKS5 代理自动配置
- ✅ Docker 容器化部署
- ✅ 跨平台支持（Windows/Linux/Mac）
- ✅ 快速启动脚本
- ✅ 完整文档

### 功能特性
- 支持 VPN Gate SSL-VPN 协议
- 自动从 VPN Gate API 获取服务器列表
- 显示服务器详细信息（国家、速度、延迟等）
- 按国家、速度、延迟筛选服务器
- 推荐分数排序
- 一键切换服务器，无需重启容器
- 实时显示连接状态
- 美观的现代化 Web 界面
- 响应式设计，支持移动设备

### 技术栈
- SoftEther VPN Client
- Dante SOCKS5 Proxy
- Flask (Python)
- Docker & Docker Compose
- HTML/CSS/JavaScript

### 文档
- 快速开始指南
- Windows 用户指南
- 完整使用文档
- 项目结构说明
- 使用演示文档

## [0.1.0] - 2024-01-XX

### 新增
- 初始项目结构
- 基础 Docker 配置
- SoftEther VPN Client 集成
- Dante SOCKS5 代理配置

---

## 版本说明

### 版本号格式
- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

### 更新类型
- **新增**：新功能
- **变更**：现有功能的变更
- **弃用**：即将移除的功能
- **移除**：已移除的功能
- **修复**：错误修复
- **安全**：安全相关的修复

---

[Unreleased]: https://github.com/yourusername/vpngate-socks5/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/vpngate-socks5/releases/tag/v1.0.0
[0.1.0]: https://github.com/yourusername/vpngate-socks5/releases/tag/v0.1.0
