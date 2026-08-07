# 🚀 Weirdhost Auto Renew

> 基于 GitHub Actions 的 Weirdhost 账号自动续期工具 · SeleniumBase UC + sing-box 代理 · 多账号支持

![Status](https://img.shields.io/badge/Status-Stable-brightgreen?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)
![Language](https://img.shields.io/badge/Made%20with-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Proxy](https://img.shields.io/badge/Proxy-hysteria2%7Cvless%7Cvmess%7Ctrojan-9C27B0?style=flat-square)

### 注册地址：https://hub.weirdhost.xyz

---

## ✨ 项目特点

| 特性 | 说明 |
|------|------|
| 🛡️ **CF 反检测** | SeleniumBase UC 模式，绕过 Cloudflare Turnstile |
| 🌐 **代理转发** | 内置 sing-box，支持 hysteria2 等 Chrome 不原生支持的协议 |
| 🍪 **智能 Cookie 注入** | CDP setCookie + Selenium add_cookie + document.cookie 三重备用 |
| ⏰ **自动运行** | 默认每天北京时间 12:20 (UTC 04:20) 触发 |
| 👥 **多账号** | 通过 `WEIRDHOST_COOKIE_N` 最多支持 5 个账号 |
| 🔔 **TG 通知** | 续期结果推送到 Telegram |
| 🔄 **自动刷新 Cookie** | 配置 `REPO_TOKEN` 后自动更新失效 Cookie |
| 🐛 **调试友好** | 失败时自动保存截图 + HTML + sing-box 日志到 artifact |

---

## 📦 一键部署流程

### Step 1：Fork 仓库

点击右上角 **Fork** 把仓库 fork 到你的账户。

### Step 2：配置 Secrets

进入你 fork 后的仓库 → **Settings → Secrets and variables → Actions → New repository secret**

#### 🔑 必填

| Secret 名称 | 示例值 | 说明 |
|:--|:--|:--|
| `WEIRDHOST_COOKIE_1` | `我的账号-----remember_web_59ba36addc2b2f940CCCC=XXXXXXXXXXX` | 账号1 的 Cookie（支持备注前缀） |
| `WEIRDHOST_COOKIE_2` | `我的账号-----remember_web_59ba36addc2b2f940CCCC=XXXXXXXXXXX` | 账号2 的 Cookie（可选） |
| `WEIRDHOST_COOKIE_3` | `我的账号-----remember_web_59ba36addc2b2f940CCCC=XXXXXXXXXXX` | 账号3 的 Cookie（可选） |
| ... | `...` | 最多支持 5 个账号（1~5） |

#### 🌐 强烈推荐（绕过 CF 对 GHA IP 的封禁）

| Secret 名称 | 示例值 | 说明 |
|:--|:--|:--|
| `PROXY_NODE` | `hysteria2://auth@server:port?sni=xxx&insecure=1` | 代理节点的完整分享链接（Chrome 不支持的协议由 sing-box 转发） |

⚠️ **为什么需要代理**：GitHub Actions 的 Azure IP 被 Cloudflare 严格风控，**不配代理基本无法通过 Turnstile**。

⚠️ **变量名**：是 `PROXY_NODE`（不是 `PROXY_URL`）。`PROXY_NODE` 接受原始协议链接（hysteria2/vless/vmess/trojan 等），由 sing-box 转成本地 SOCKS5 给 Chrome 用。

#### 🔧 可选

| Secret 名称 | 示例值 | 说明 |
|:--|:--|:--|
| `REPO_TOKEN` | `ghp_xxxxxxxxxxxx` | GitHub PAT，用于自动更新 Cookie（强烈推荐配置） |
| `TG_BOT_TOKEN` | `123456789:ABC-XYZ...` | Telegram Bot Token（用于通知） |
| `TG_CHAT_ID` | `123456789` | Telegram Chat ID（用于通知） |

---

## 📌 Cookie 获取方法

每个账号的 Cookie 需要以 **`备注-----remember_web_xxx=yyy`** 的格式填写到对应的 `WEIRDHOST_COOKIE_N` 中：

### 1. 获取 Cookie

1. 打开 https://hub.weirdhost.xyz 登录账号
2. 按 `F12` → 切换到 **Application** 标签
3. 左侧选 **Cookies** → `https://hub.weirdhost.xyz`
4. 找到以 `remember_web_` 开头的 Cookie
5. **复制 Value 列的内容**（不要复制整个 Cookie 请求头！）

### 2. 格式化 Cookie

格式：`备注-----remember_web_xxx=yyy`

- `备注`：自定义标识（可留空，但建议保留便于识别）
- `-----`：分隔符（5 个连字符，固定）
- `remember_web_xxx=yyy`：完整的 Cookie 键值对

**示例**：

```
我的主账号-----remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d=eyJpdiI6...
```

如果不需要备注，也可以直接填写纯 Cookie：

```
remember_web_59ba36addc2b2f9401580f014c7f58ea4e30989d=eyJpdiI6...
```

⚠️ **如果误从 Network 标签复制了整段 Cookie 请求头**（包含 `;` 分隔的多个 cookie），脚本会自动截断到第一个 `;` 之前的部分，但建议尽量用 Application 标签只复制单个 Cookie 的 value。

---

## 🌐 PROXY_NODE 支持的协议

### Hysteria2（推荐）

```
hysteria2://auth_secret@server:port?sni=example.com&insecure=1#name
```

参数说明：
- `auth_secret`：密码（URL path 的 username 部分）
- `sni`：TLS SNI（可选，默认等于 server）
- `insecure`：是否跳过证书验证（`0` 或 `1`，可选，默认 `0`）

更多协议（vless/vmess/trojan/ss/tuic）支持正在开发中，当前版本仅支持 hysteria2/hy2。

---

## 🚀 触发续期

### 自动触发

默认每天 **北京时间 12:20（UTC 04:20）** 自动运行。

### 手动触发

1. 进入仓库的 **Actions** 标签
2. 左侧选择 `Weirdhost 多账号自动续期`
3. 右上角点 `Run workflow` → `Run workflow`

---

## 📂 项目结构

```
├── .github/
│   └── workflows/
│       └── Weirdhost_renew.yml   # GHA 工作流
├── scripts/
│   ├── weirdhost_renew.py       # 续期主脚本（SeleniumBase UC）
│   └── start_singbox.sh         # sing-box 启动脚本
├── img/                         # 说明用图
└── README.md
```

---

## 🛠️ 工作原理

```
┌──────────────────────────────────────────────────────────┐
│                  GitHub Actions Runner                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │  start_singbox.sh                                │    │
│  │  ├─ 解析 PROXY_NODE (hysteria2://...)            │    │
│  │  ├─ 生成 sing-box 配置                           │    │
│  │  └─ setsid 启动 sing-box 监听 127.0.0.1:1080     │    │
│  └──────────────────────────────────────────────────┘    │
│                       │                                  │
│                       ▼                                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │  weirdhost_renew.py                              │    │
│  │  ├─ Chrome --proxy-server=socks5://127.0.0.1:1080│    │
│  │  ├─ SeleniumBase UC 模式绕过 CF Turnstile       │    │
│  │  ├─ CDP setCookie 注入 remember_web_xxx         │    │
│  │  └─ 调用 Weirdhost API 续期服务器                │    │
│  └──────────────────────────────────────────────────┘    │
│                       │                                  │
└───────────────────────┼──────────────────────────────────┘
                        ▼
                ┌─────────────────┐
                │  Hysteria2 节点  │
                │  (例如日本 AWS)  │
                └─────────────────┘
                        ▼
                ┌─────────────────┐
                │  hub.weirdhost.xyz │
                │  (CF 验证通过)    │
                └─────────────────┘
```

---

## 🔍 调试

如果运行失败，可以从 Actions 运行页面下载以下 artifact 排查：

| Artifact 名称 | 内容 |
|--------------|------|
| `debug-screenshots` | 失败时截图（CF 挑战页、登录失败页等） |
| `debug-html` | 失败时页面源码 |
| `singbox-log` | sing-box 完整日志（代理连接情况） |

---

## ❓ 常见问题

### Q1: 续期失败，日志显示 "Cloudflare 验证未通过"

**原因**：CF 拦截了 GitHub IP。

**解决**：配置 `PROXY_NODE` Secret，使用住宅代理（推荐日本/韩国节点）。

### Q2: 日志显示 "ERR_PROXY_CONNECTION_FAILED"

**原因**：sing-box 没启动或代理节点失效。

**解决**：
1. 检查 `PROXY_NODE` Secret 是否存在
2. 下载 `singbox-log` artifact 查看 sing-box 启动日志
3. 用本地客户端（v2rayN/NekoBox）测试代理节点是否可用

### Q3: 日志显示 "Cookie 注入失败"

**原因**：Cookie 格式错误或 Cookie 已过期。

**解决**：
1. 重新从浏览器 **Application → Cookies** 复制 `remember_web_xxx` 的 value
2. 不要从 **Network → Request Headers → Cookie:** 复制整段（虽然脚本会自动截断，但容易出错）
3. 确认 Cookie 未过期（登录态通常 7-30 天）

### Q4: 日志显示 "PROXY_NODE 环境变量为空"

**原因**：没配置 `PROXY_NODE` Secret。

**解决**：去仓库 Settings → Secrets → Actions 添加 `PROXY_NODE` Secret。

### Q5: 支持哪些代理协议？

当前仅支持 **hysteria2/hy2**。如果你需要 vless/vmess/trojan 等协议，可以自行修改 `scripts/start_singbox.sh` 添加 case 分支。

---

## 📝 注意事项

⚠️ **免责声明**：本项目仅供学习交流使用，请合理合法使用免费资源，遵守 Weirdhost 的用户条款。

⚠️ Cookie 有效期有限，建议配置 `REPO_TOKEN` 实现自动更新。

⚠️ 建议配置代理以提高成功率，避免 Cloudflare 拦截。

---

## 🙏 参考项目

- [oyz8/weirdhost-login](https://github.com/oyz8/weirdhost-login) - 原项目

## License

MIT License
