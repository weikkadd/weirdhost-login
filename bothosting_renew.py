#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weirdhost 自动续期脚本 - 基于 seleniumbase 的 undetected Chrome
支持 Turnstile 验证处理和多账号管理
"""

import os
import re
import sys
import time
import json
import logging
import requests
import subprocess
from datetime import datetime
from seleniumbase import SB

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('renew.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 环境变量配置
EMAIL = os.environ.get("EMAIL") or ""
SESSION_TOKEN = os.environ.get("SESSION_TOKEN") or ""
COOKIE = os.environ.get("WEIRDHOST_COOKIE") or ""
CF_CLEARANCE = os.environ.get("CF_CLEARANCE") or ""
GH_TOKEN = os.environ.get("GH_TOKEN") or ""
TG_CHAT_ID = os.environ.get("TG_CHAT_ID") or ""
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or ""
IS_PROXY = os.environ.get("IS_PROXY", "false").lower() == "true"
PROXY_SERVER = os.environ.get("PROXY_SERVER", "").strip() or "http://127.0.0.1:1080"
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"
WEIRDHOST_URL = os.environ.get("WEIRDHOST_URL") or "https://hub.weirdhost.xyz"

# 构造 cookie
COOKIES = {
    "session_token": SESSION_TOKEN,
    "login": "true",
    "theme": "system",
}

# 记录登录方式
_LOGIN_METHOD = "COOKIE"

def get_current_ip():
    """获取当前出口 IP"""
    try:
        proxies = {"http": PROXY_SERVER, "https": PROXY_SERVER} if IS_PROXY else None
        response = requests.get("https://api.ip.sb/ip", proxies=proxies, timeout=15)
        return response.text.strip()
    except Exception as e:
        logger.error(f"获取 IP 失败: {e}")
        return "Unknown"

def wait_for_turnstile_pass(sb, timeout=30):
    """等待 Turnstile 验证通过"""
    start = time.time()
    cf_indicators = ["verify you are human", "确认您是真人", "troubleshoot", "just a moment"]
    
    while time.time() - start < timeout:
        try:
            page_lower = sb.get_page_source().lower()
            if not any(x in page_lower for x in cf_indicators):
                logger.info("✅ Turnstile 验证已通过")
                return True
        except:
            pass
        sb.sleep(1)
    
    logger.error("❌ Turnstile 验证超时")
    return False

def handle_turnstile(sb, max_attempts=5):
    """处理 Turnstile 验证"""
    logger.info("🔒 检测到 Cloudflare 验证，开始处理...")
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"尝试点击 Turnstile {attempt}/{max_attempts}...")
        try:
            # 使用 seleniumbase 的自动点击功能
            sb.uc_gui_click_captcha()
            time.sleep(12)
            
            # 等待验证通过
            if wait_for_turnstile_pass(sb, timeout=25):
                logger.info(f"✅ 第 {attempt} 次尝试成功")
                return True
            else:
                logger.warning(f"第 {attempt} 次尝试未通过，刷新页面重试...")
                sb.refresh()
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"点击 Turnstile 失败: {e}")
            time.sleep(2)
    
    logger.error("❌ 所有 Turnstile 处理尝试都失败")
    return False

def check_session_valid(sb):
    """检查会话是否有效"""
    try:
        # 访问仪表盘页面
        sb.open(f"{WEIRDHOST_URL}/dashboard")
        sb.wait_for_ready_state_complete()
        time.sleep(3)
        
        current_url = sb.get_current_url()
        logger.info(f"当前 URL: {current_url}")
        
        # 检查是否登录成功
        if "login" in current_url.lower():
            logger.warning("会话已过期，需要重新登录")
            return False
        
        if "dashboard" in current_url or "账户" in sb.get_title():
            logger.info("✅ 会话有效")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"检查会话时出错: {e}")
        return False

def renew_session(sb):
    """续期会话"""
    logger.info("=" * 60)
    logger.info("执行会话续期...")
    logger.info("=" * 60)
    
    try:
        # 访问续期端点
        logger.info("访问续期端点...")
        sb.open(f"{WEIRDHOST_URL}/login/check")
        sb.wait_for_ready_state_complete()
        time.sleep(5)
        
        # 检查是否成功
        current_url = sb.get_current_url()
        page_source = sb.get_page_source()
        
        logger.info(f"续期后 URL: {current_url}")
        
        if "login" not in current_url.lower():
            logger.info("✅ 续期成功")
            return True
        else:
            logger.warning("⚠️ 续期可能失败，会话已过期")
            return False
            
    except Exception as e:
        logger.error(f"续期会话时出错: {e}")
        return False

def send_telegram_message(message: str):
    """发送 Telegram 通知"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        logger.info("⚠️ Telegram 未配置，跳过通知")
        return
    
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": TG_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("✅ Telegram 通知已发送")
        else:
            logger.warning(f"⚠️ Telegram 通知发送失败: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Telegram 发送失败: {e}")

def format_notification(status: str, extra: str = "", error: str = "") -> str:
    """格式化通知消息"""
    local_time = time.gmtime(time.time() + 8 * 3600)
    now = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
    
    lines = [
        "🇯🇵 Weirdhost 自动续期通知",
        "",
        f"{status}",
    ]
    
    if EMAIL:
        lines.append(f"👤 登录账户: {EMAIL}")
    
    if extra:
        lines.append(extra)
    
    if error:
        lines.append(f"⚠️ 错误信息: {error}")
    
    lines.append(f"⏱️ 执行时间: {now}")
    lines.append(f"🌐 网站: {WEIRDHOST_URL}")
    
    return "\n".join(lines)

def update_github_secret(secret_name, new_value):
    """更新 GitHub Secret"""
    if not new_value or not GH_TOKEN:
        logger.warning(f"⚠️ 跳过更新 {secret_name}：缺少值或 GH_TOKEN")
        return False
    
    masked = new_value[:4] + "..." + new_value[-4:] if len(new_value) > 8 else "***"
    logger.info(f"🔄 更新 Secret: {secret_name} (新值: {masked})")
    
    try:
        env = os.environ.copy()
        env["GH_TOKEN"] = GH_TOKEN
        
        proc = subprocess.run(
            ["gh", "secret", "set", secret_name, "--body", new_value],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env
        )
        
        if proc.returncode == 0:
            logger.info("✅ Secret 更新成功")
            return True
        else:
            logger.error(f"❌ 更新失败: {proc.stderr.strip()}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 异常: {e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始 Bot-Hosting / Weirdhost 自动续期")
    logger.info("=" * 60)
    
    # 获取出口 IP
    ip = get_current_ip()
    logger.info(f"📍 当前出口 IP: {ip}")
    logger.info(f"🔗 代理状态: {'已启用' if IS_PROXY else '未启用'}")
    logger.info(f"🎭 Headless 模式: {'启用' if HEADLESS else '禁用'}")
    logger.info(f"🌐 目标网站: {WEIRDHOST_URL}")
    
    # 配置 seleniumbase
    sb_kwargs = {
        "uc": True,  # 启用 undetected chrome
        "headless": HEADLESS,
        "disable_csp": True,  # 禁用 CSP 提高兼容性
        "disable_webgl": True,  # 禁用 WebGL 降低指纹特征
    }
    
    if IS_PROXY and PROXY_SERVER:
        sb_kwargs["proxy"] = PROXY_SERVER
    
    global _LOGIN_METHOD
    
    with SB(**sb_kwargs) as sb:
        try:
            # 注入 Cookie
            logger.info("📝 注入 Cookie...")
            if COOKIE:
                sb.add_cookie({
                    "name": "remember_web",
                    "value": COOKIE,
                    "domain": "hub.weirdhost.xyz",
                    "path": "/"
                })
                logger.info(f"✅ Cookie 已注入 (长度: {len(COOKIE)})")
            elif SESSION_TOKEN:
                for name, value in COOKIES.items():
                    if value:
                        sb.add_cookie({
                            "name": name,
                            "value": value,
                            "domain": "hub.weirdhost.xyz",
                            "path": "/"
                        })
                logger.info("✅ Session Token 已注入")
            else:
                logger.error("❌ 未配置 Cookie 或 Session Token")
                send_telegram_message(format_notification("❌ 配置错误", error="缺少 Cookie 或 Session Token"))
                return False

            # 注入 CF_CLEARANCE
            if CF_CLEARANCE:
                clearance_name = CF_CLEARANCE.split("=")[0] if "=" in CF_CLEARANCE else "cf_clearance"
                clearance_value = CF_CLEARANCE.split("=", 1)[1] if "=" in CF_CLEARANCE else CF_CLEARANCE
                sb.add_cookie({
                    "name": clearance_name,
                    "value": clearance_value,
                    "domain": "hub.weirdhost.xyz",
                    "path": "/"
                })
                logger.info(f"✅ CF_CLEARANCE 已注入 ({len(CF_CLEARANCE)} 字符)")
            else:
                logger.warning("⚠️ 未配置 CF_CLEARANCE，可能需要手动通过 Cloudflare 验证")
            
            # 访问网站
            logger.info(f"🌐 访问 {WEIRDHOST_URL}...")
            sb.open(WEIRDHOST_URL)
            sb.wait_for_ready_state_complete()
            time.sleep(3)
            
            # 处理 Cloudflare 验证
            time.sleep(3)
            current_url = sb.get_current_url()
            page_title = sb.get_title()
            logger.info(f"当前 URL: {current_url}")
            logger.info(f"页面标题: {page_title}")
            
            if "challenge" in current_url.lower() or "just a moment" in page_title.lower() or ".cloudflare" in current_url.lower():
                logger.info("🛡️ 检测到 Cloudflare 验证")
                if not handle_turnstile(sb):
                    logger.error("❌ Cloudflare 验证失败")
                    sb.save_screenshot("cf_challenge_failed.png")
                    send_telegram_message(format_notification(
                        "❌ Cloudflare 验证失败",
                        error="无法通过 Turnstile 验证"
                    ))
                    return False
            else:
                logger.info("✅ 未检测到 Cloudflare 验证，继续...")
            
            # 检查会话状态
            if not check_session_valid(sb):
                logger.error("❌ 会话已过期")
                sb.save_screenshot("session_expired.png")
                send_telegram_message(format_notification(
                    "❌ 会话已过期",
                    error="Cookie 已失效，请更新"
                ))
                return False
            
            # 执行续期
            if not renew_session(sb):
                logger.error("❌ 续期失败")
                sb.save_screenshot("renew_failed.png")
                send_telegram_message(format_notification(
                    "❌ 续期失败",
                    error="续期请求失败"
                ))
                return False
            
            # 成功
            logger.info("✅ 续期成功")
            sb.save_screenshot("success.png")
            send_telegram_message(format_notification(
                "✅ 续期成功",
                extra=f"🌐 网站: {WEIRDHOST_URL}\n📍 IP: {ip}\n🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ))
            return True
            
        except Exception as e:
            logger.error(f"❌ 脚本执行失败: {e}")
            sb.save_screenshot("error.png") if 'sb' in locals() else None
            send_telegram_message(format_notification(
                "❌ 脚本执行失败",
                error=str(e)[:200]
            ))
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
