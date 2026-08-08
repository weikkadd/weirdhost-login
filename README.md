# Weirdhost 自动续期 & 多账号版

基于 GitHub Actions 的 Weirdhost VPN 自动续期工具，支持多账号管理。

## 功能说明

- ✅ 多账号自动续期
- ✅ 支持定时 Cron 触发
- ✅ 支持手动触发（Workflow Dispatch）
- ✅ Cookie 状态检查
- ✅ 日志记录
- ✅ 随机延迟，模拟人工操作

## 部署步骤

### 1. Fork 本仓库

### 2. 获取 Cookie

1. 登录 Weirdhost 网站
2. 打开浏览器开发者工具 (F12)
3. 进入 Application → Cookies
4. 找到以 `remember_web_` 开头的 Cookie
5. 复制完整的 `名称=值`

示例输出：
```
remember_web_56ba69108584858d=eyJpZCI6MSwiZXhwIjoxNjg5MjM0NTY3fQ.abcdef123456
```

### 3. 配置 GitHub Secrets

在 GitHub 仓库中，进入 Settings → Secrets and variables → Actions，添加以下 secrets：

#### 单个账号模式：
| Secret 名称 | 说明 |
|------------|------|
| `WEIRDHOST_COOKIE` | 单个账号的 Cookie |

#### 多账号模式（推荐）：
| Secret 名称 | 说明 |
|------------|------|
| `WEIRDHOST_ACCOUNTS` | JSON 格式的账号列表 |

**多账号 JSON 格式示例：**
```json
[
  {
    "name": "账号1",
    "cookie": "remember_web_XXXXXXXXXXXXXXXX=YYYYYYYY;"
  },
  {
    "name": "账号2", 
    "cookie": "remember_web_AAAAAAAAAAAAAAAAAA=BBBBBBBB;"
  }
]
```

### 4. 配置 GitHub Actions

确保 GitHub Actions 已启用：
1. 进入 Settings → Actions → General
2. 选择 "Allow all actions and reusable workflows"

### 5. 触发续期

- **自动续期**：每周一 UTC 00:00 自动执行
- **手动续期**：点击 Actions 标签页，选择 "Weirdhost Auto Renew"，点击 "Run workflow"

## 文件结构

```
.github/workflows/
  ├── weirdhost_renew.yml    # 自动续期工作流
  ├── deploy.yml             # 部署工作流
  └── account-manage.yml     # 账号管理工作流
main.py                      # 主脚本
config.json                  # 配置文件
requirements.txt             # Python 依赖
```

## 日志查看

日志保存在：
- `.github/workflows` 运行日志（GitHub Actions 界面）
- `logs/renew.log`（本地日志文件）

## 注意事项

1. **Cookie 有效期**：Cookie 通常有效期为 30-90 天，建议每周续期一次
2. **频率控制**：脚本包含随机延迟，避免频繁请求
3. **多账号支持**：可以管理多个 Weirdhost 账号，批量续期

## 免责声明

本项目仅供学习研究使用。使用者需自行承担一切后果。

## 相关链接

- [Weirdhost 官网](https://weirdhost.net)
- [GitHub Actions 文档](https://docs.github.com/cn/actions)
