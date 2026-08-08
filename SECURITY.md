# 安全说明

## 环境变量配置

以下敏感信息应通过 GitHub Secrets 配置，**不要**直接写在代码中：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token | Cloudflare Dashboard → Account API tokens |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Account ID | Cloudflare Dashboard → Account settings |
| `WORKER_NAME` | Worker 脚本名称 | Cloudflare Dashboard → Workers |
| `WORKER_SUBDOMAIN` | Worker 子域名 | 如 `pellafree` |
| `MS_ACCESS_TOKEN` | Microsoft Access Token | Microsoft Graph API 授权 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | @BotFather |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | 获取方式见下方 |

## 获取 Cloudflare API Token

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **Account** → **API tokens**
3. 点击 **Create Token**
4. 选择 **Edit Cloudflare Workers** 权限模板
5. 选择对应的 Account 和 Zone
6. 复制生成的 Token

## 获取 Telegram Chat ID

1. 在 Telegram 搜索 `@userinfobot`
2. 发送任意消息，获取您的 Chat ID

## 安全建议

1. **不要**将 API Token 提交到代码仓库
2. **不要**在日志中打印敏感信息
3. 定期轮换 API Token
4. 使用最小权限原则配置 API Token
