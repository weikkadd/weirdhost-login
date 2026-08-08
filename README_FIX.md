# Weirdhost 自动续期 - Cloudflare Turnstile 问题修复方案

## 问题诊断

根据日志分析，主要问题：

1. **反检测脚本注入失败**: `PermissionManager is not defined`
   - 原因：尝试访问 Chrome 内部 API 失败

2. **Cloudflare Turnstile 验证失败**:
   - 多次尝试点击验证码但无法通过
   - 页面始终停留在 "Just a moment..." 挑战页

## 解决方案

### 方案一：使用 Selenium 替代 Playwright（推荐）

创建了修复版脚本 `weirdhost_renew_v2.py`，主要改进：

1. **修复反检测脚本**
   - 使用 CDP 命令注入反检测代码
   - 避免访问不存在的 `PermissionManager`

2. **优化 Turnstile 处理**
   - 检测 Turnstile 容器并尝试绕过
   - 增加等待时间和重试逻辑

3. **添加调试功能**
   - 自动保存截图和 HTML
   - Telegram 通知失败信息

### 方案二：手动获取 CF_CLEARANCE

1. 在本地浏览器登录 Weirdhost
2. 打开开发者工具 → Application → Cookies
3. 复制 `cf_clearance` 的值
4. 添加到 GitHub Secrets: `CF_CLEARANCE`

### 方案三：使用第三方 CAPTCHA 服务

集成 2Captcha 或 AntiCaptcha 服务自动解决 Turnstile。

## 部署步骤

1. 替换原有的 `weirdhost_renew.py` 为 `weirdhost_renew_v2.py`
2. 更新 `requirements.txt` 为 `requirements_v2.txt`
3. 配置新的 GitHub Secrets:
   - `WEIRDHOST_COOKIE`
   - `CF_CLEARANCE` (可选)
   - `PROXY_URL` (推荐日本/韩国代理)
   - `TELEGRAM_BOT_TOKEN` (可选)
   - `TELEGRAM_CHAT_ID` (可选)

## 代理建议

使用日本或韩国代理可以提高成功率：
- 日本 IP: `socks5://xxx:port`
- 韩国 IP: `socks5://xxx:port`

## 日志位置

- GitHub Actions 日志: 工作流运行页面
- 本地日志: `renew.log`
- 截图: `screenshots/` 目录

## 免责声明

本项目仅供学习研究使用。使用者需自行承担一切后果。
