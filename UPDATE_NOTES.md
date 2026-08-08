# 更新说明

## 问题诊断

### 失败原因
之前的修复尝试使用了浏览器自动化（Selenium/Playwright），但在 GitHub Actions 的 headless 环境中：
1. `xdotool` 需要图形界面才能点击验证码
2. Cloudflare Turnstile 验证无法通过自动化点击
3. 浏览器指纹容易被检测

### 成功原因
原有的工作流使用纯 API 调用（curl），不依赖浏览器，因此：
1. 不受 headless 环境限制
2. 不需要处理 Cloudflare 验证
3. 更简单、更稳定

## 修复内容

### 1. 简化工作流
- ✅ 移除浏览器自动化
- ✅ 使用纯 API 调用（curl）
- ✅ 添加 Telegram 失败通知
- ✅ 优化多账号支持

### 2. 关键改进
```yaml
# 使用纯 API 调用
curl -X POST "${URL}/login/check" \
  -H "Cookie: ${COOKIE}" \
  -H "Content-Type: application/json" \
  -d '{}'

# 检查响应
if echo "$response" | grep -q '"success"\|true\|200'; then
  echo "✅ 续期成功"
else
  echo "❌ 续期失败"
fi
```

### 3. 新增功能
- Telegram 失败通知
- 更详细的日志输出
- 更好的错误处理

## 配置说明

### GitHub Secrets
```json
[
  {
    "name": "账号1",
    "cookie": "remember_web_XXXXXXXXXXXXXXXX=YYYYYYYY;",
    "url": "https://hub.weirdhost.xyz"
  }
]
```

### 可选 Secrets
- `TELEGRAM_BOT_TOKEN` - Telegram Bot Token
- `TELEGRAM_CHAT_ID` - Telegram Chat ID

## 部署步骤

1. **更新工作流文件**
   ```bash
   # 已更新 .github/workflows/weirdhost_renew.yml
   ```

2. **提交代码**
   ```bash
   git add .
   git commit -m "fix: 使用纯 API 调用替代浏览器自动化"
   git push
   ```

3. **触发工作流**
   - 自动：每 3 天执行一次
   - 手动：点击 Actions → "Weirdhost 多账号自动续期" → "Run workflow"

## 验证方法

工作流运行成功后，你应该看到：
- ✅ "开始 Weirdhost 自动续期"
- ✅ "处理账号: xxx"
- ✅ "✅ 续期成功" 或 "❌ 续期失败"
- ✅ 没有浏览器相关的错误

## 注意事项

1. **Cookie 有效期**：Cookie 通常有效期为 30-90 天
2. **续期频率**：建议每 3 天续期一次
3. **代理设置**：如需代理，在 Cookie 后添加代理配置
4. **失败通知**：配置 Telegram 可以及时收到失败通知

## 回滚方案

如果新版本有问题，可以回滚到之前的版本：
```bash
git revert <commit-hash>
git push
```

## 联系支持

如有问题，请查看：
- GitHub Actions 日志
- `renew.log` 文件
- Telegram 通知（如果配置）
