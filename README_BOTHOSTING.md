# Bot-Hosting / Weirdhost 自动续期脚本

基于 seleniumbase 的 undetected Chrome 浏览器自动化续期工具。

## 功能特性

- ✅ 支持 Turnstile 验证自动处理
- ✅ 多账号管理
- ✅ Telegram 通知
- ✅ 自动更新 GitHub Secrets
- ✅ 代理支持
- ✅ Headless 模式

## 安装依赖

```bash
pip install -r requirements_bothosting.txt
seleniumbase install chromium
```

## 配置环境变量

复制 `.env.example` 为 `.env` 并填写实际值：

```bash
cp .env.example .env
```

## GitHub Secrets 配置

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `EMAIL` | 邮箱（通知用） | user@example.com |
| `SESSION_TOKEN` | Session Token | abc123... |
| `WEIRDHOST_COOKIE` | 完整 Cookie | remember_web_XXX=YYY; |
| `GH_TOKEN` | GitHub PAT（可选） | ghp_xxx... |
| `TG_CHAT_ID` | Telegram Chat ID | 123456789 |
| `TG_BOT_TOKEN` | Telegram Bot Token | 123456:ABC-DEF... |
| `IS_PROXY` | 是否使用代理 | true |
| `PROXY_SERVER` | 代理地址 | socks5://127.0.0.1:1080 |

## 运行方式

### 本地运行
```bash
# 1. 安装依赖
pip install -r requirements_bothosting.txt
seleniumbase install chromium

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填写实际值

# 3. 运行脚本
python bothosting_renew.py
```

### GitHub Actions
```yaml
# 自动触发：每 3 天 UTC 00:00 执行
# 手动触发：Actions → Bot-Hosting 自动续期 → Run workflow
```

## Turnstile 验证说明

### 为什么能过？
1. **seleniumbase uc 模式**：注入反检测脚本，模拟真实浏览器
2. **自动点击验证码**：`uc_gui_click_captcha()` 自动处理
3. **多次重试**：最多 5 次尝试
4. **代理支持**：使用日本/韩国代理降低风险

### 提高成功率
1. **使用高质量代理**
   - 推荐日本或韩国 IP
   - 避免数据中心 IP
   - 使用 residential proxy

2. **配置 CF_CLEARANCE**
   ```bash
   # 从浏览器复制 cf_clearance cookie
   WEIRDHOST_COOKIE=remember_web_XXX=YYY; cf_clearance=ZZZ;
   ```

3. **调整运行时间**
   - 避免高峰时段
   - 分散执行时间

## 故障排除

### 1. Turnstile 验证失败
- 检查代理 IP 质量（推荐日本/韩国 residential IP）
- 尝试更换代理服务器
- 增加等待时间（修改 max_attempts 参数）
- 查看截图诊断：`cf_challenge_failed.png`

### 2. 会话已过期
- 更新 SESSION_TOKEN 或 COOKIE
- 从浏览器复制最新 Cookie：
  1. 登录网站
  2. F12 → Application → Cookies
  3. 复制 `session_token` 或 `remember_web` 的值

### 3. 脚本超时
- 修改 `.github/workflows/bot-hosting-renew.yml` 中的 `timeout-minutes`
- 检查代理网络连接
- 查看 GitHub Actions 日志详细错误

### 4. 代理连接失败
```bash
# 测试代理是否可用
curl -x socks5://127.0.0.1:1080 https://api.ip.sb/ip
```

## 日志查看

- GitHub Actions 日志：工作流运行页面
- 本地日志：`renew.log`
- 截图：`*.png` 文件

## 安全注意事项

1. **不要提交 .env 文件** - 已添加到 .gitignore
2. **定期更新 Cookie** - 建议每月检查一次
3. **使用专用 GitHub Token** - 仅授予必要权限
4. **启用 2FA** - GitHub 和 Telegram 都启用
5. **代理安全** - 使用可信的代理服务商

## 免责声明

本项目仅供学习研究使用。使用者需自行承担一切后果。

**重要提示**：
- 请遵守网站服务条款
- 不要用于商业用途
- 自行承担使用风险

## 相关链接

- [seleniumbase 文档](https://seleniumbase.io/)
- [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/)
- [GitHub Actions 文档](https://docs.github.com/cn/actions)
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)

## 更新日志

### v1.0.0 (2026-08-08)
- ✅ 初始版本
- ✅ 支持 Turnstile 验证
- ✅ 多账号管理
- ✅ Telegram 通知
