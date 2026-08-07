#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weirdhost API 直连续期脚本（无浏览器版）

完全跳过 CF 验证和浏览器自动化，直接调用 Weirdhost API 完成续期。
适用于 GitHub Actions 或其他无 GUI 环境。

工作原理：
1. 用 remember_web_xxx cookie 调用 /api/client 获取服务器列表
2. 对每个服务器调用续期 API
3. 续期 API 可能需要 cf-turnstile-response token（如果需要会跳过该服务器）

环境变量：
- WEIRDHOST_COOKIE_1 ~ WEIRDHOST_COOKIE_5: 账号 Cookie（格式：备注-----remember_web_xxx=yyy）
- PROXY_URL: HTTP/SOCKS5 代理（可选，用于绕过 CF IP 风控）
- TG_BOT_TOKEN / TG_CHAT_ID: TG 通知（可选）
"""

import os
import sys
import json
import time
import random
import requests
from urllib.parse import unquote, quote
from datetime import datetime, timedelta

# 尝试导入 curl_cffi（伪装 TLS 指纹，绕过 CF）
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

sys.stdout.reconfigure(line_buffering=True)

# ==================== 配置 ====================
BASE_URL = "https://hub.weirdhost.xyz"
API_BASE = f"{BASE_URL}/api/client"
DOMAIN = "hub.weirdhost.xyz"
MAX_COOKIE_COUNT = 5

# 代理配置
PROXY_URL = os.environ.get("PROXY_URL", "").strip()

# 构造 requests session
def make_session():
    # 优先用 curl_cffi（伪装 TLS 指纹）
    if HAS_CURL_CFFI:
        print(f"[INFO] 使用 curl_cffi（Chrome TLS 指纹，绕过 CF）")
        s = cffi_requests.Session(impersonate="chrome120")
    else:
        print(f"[WARN] curl_cffi 未安装，使用普通 requests（可能被 CF 拦截）")
        s = requests.Session()

    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8,zh-CN;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE_URL + "/",
        "Origin": BASE_URL,
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    })
    if PROXY_URL:
        s.proxies.update({"http": PROXY_URL, "https": PROXY_URL})
        print(f"[INFO] 使用代理: {PROXY_URL}")
    return s


# ==================== 工具函数 ====================

def mask_text(text, show=3):
    if not text:
        return "***"
    text = str(text)
    if len(text) <= show * 2:
        return "*" * len(text)
    return text[:show] + "*" * (len(text) - show * 2) + text[-show:]


def parse_cookie(raw_value):
    """解析 WEIRDHOST_COOKIE_N 环境变量"""
    if not raw_value:
        return None
    raw_value = raw_value.strip()
    remark = ""
    cookie_str = raw_value
    if "-----" in raw_value:
        parts = raw_value.split("-----", 1)
        remark = parts[0].strip()
        cookie_str = parts[1].strip() if len(parts) > 1 else ""
    # 兼容整段 Cookie 请求头（截断到第一个 ;）
    if ";" in cookie_str:
        cookie_str = cookie_str.split(";", 1)[0].strip()
    if "=" not in cookie_str:
        return None
    parts = cookie_str.split("=", 1)
    name = parts[0].strip()
    value = parts[1].strip()
    if not name.startswith("remember_web"):
        return None
    return {
        "remark": remark or "账号",
        "name": name,
        "value": value,
        "raw": f"{name}={value}",
    }


def detect_accounts():
    accounts = []
    for i in range(1, MAX_COOKIE_COUNT + 1):
        env_name = f"WEIRDHOST_COOKIE_{i}"
        raw = os.environ.get(env_name, "").strip()
        if not raw:
            continue
        cfg = parse_cookie(raw)
        if not cfg:
            print(f"[WARN] {env_name} 格式错误，跳过")
            continue
        print(f"[INFO] 检测到 {env_name}: {mask_text(cfg['remark'])}")
        accounts.append({
            "index": i,
            "env_name": env_name,
            **cfg,
        })
    return accounts


def get_xsrf_token(session):
    """从 session cookies 获取 XSRF-TOKEN"""
    try:
        # curl_cffi 的 cookies 是 dict-like
        if HAS_CURL_CFFI and hasattr(session.cookies, 'get'):
            token = session.cookies.get("XSRF-TOKEN")
        else:
            token = session.cookies.get("XSRF-TOKEN")
        if token:
            return unquote(token)
    except Exception as e:
        print(f"[WARN] 获取 XSRF-TOKEN 异常: {e}")
    return None


def api_get(session, url, xsrf_token=None, timeout=30):
    """GET 请求 API"""
    headers = {}
    if xsrf_token:
        headers["X-XSRF-TOKEN"] = xsrf_token
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 401:
            return {"_error": "unauthorized"}
        return resp.json()
    except Exception as e:
        return {"_error": str(e)}


def api_post(session, url, data=None, xsrf_token=None, timeout=30):
    """POST 请求 API"""
    headers = {
        "Content-Type": "application/json",
    }
    if xsrf_token:
        headers["X-XSRF-TOKEN"] = xsrf_token
    try:
        resp = session.post(url, headers=headers, json=data, timeout=timeout)
        if resp.status_code == 401:
            return {"_error": "unauthorized"}
        return resp.json()
    except Exception as e:
        return {"_error": str(e)}


# ==================== 主流程 ====================

def renew_account(session, account):
    """续期单个账号"""
    result = {
        "remark": account["remark"],
        "env_name": account["env_name"],
        "status": "unknown",
        "message": "",
        "servers": [],
    }

    print(f"\n{'=' * 60}")
    print(f"[INFO] 处理账号 [{account['index']}]: {mask_text(account['remark'])}")
    print(f"{'=' * 60}")

    # 注入 cookie
    try:
        session.cookies.set(account["name"], account["value"], domain=DOMAIN, path="/")
    except Exception:
        # curl_cffi 兼容方式
        session.cookies.set({
            "name": account["name"],
            "value": account["value"],
            "domain": DOMAIN,
            "path": "/",
        })

    # 先访问首页（建立 session + 获取 XSRF-TOKEN）
    print(f"[INFO] [步骤1] 访问首页获取 session...")
    try:
        resp = session.get(BASE_URL + "/", timeout=30, allow_redirects=True)
        print(f"[INFO]   首页状态码: {resp.status_code}")
        # 兼容 curl_cffi 和 requests 的 cookies 访问方式
        try:
            cookie_names = list(session.cookies.keys())
        except Exception:
            cookie_names = list(session.cookies.dict.keys()) if hasattr(session.cookies, 'dict') else []
        print(f"[INFO]   当前 cookies: {cookie_names}")
    except Exception as e:
        print(f"[ERROR] 首页访问失败: {e}")
        result["status"] = "error"
        result["message"] = f"首页访问失败: {e}"
        return result

    # 检查是否被 CF 拦截（如果有 cdn-cgi 路径或 cf-mitigated 头）
    if "cf-mitigated" in resp.headers or "/cdn-cgi/" in resp.url:
        print(f"[WARN] 检测到 Cloudflare 拦截")
        result["status"] = "cf_blocked"
        result["message"] = "Cloudflare 拦截（API 模式可能需要配置代理）"
        return result

    xsrf_token = get_xsrf_token(session)
    if not xsrf_token:
        print(f"[ERROR] 未获取到 XSRF-TOKEN，可能 Cookie 失效")
        result["status"] = "cookie_invalid"
        result["message"] = "Cookie 失效（未获取到 XSRF-TOKEN）"
        return result
    print(f"[INFO]   XSRF-TOKEN 已获取")

    # [步骤2] 获取服务器列表
    print(f"[INFO] [步骤2] 获取服务器列表...")
    server_data = api_get(session, f"{API_BASE}?page=1", xsrf_token)
    if not server_data or server_data.get("_error"):
        err = server_data.get("_error") if server_data else "无响应"
        print(f"[ERROR]   获取服务器列表失败: {err}")
        result["status"] = "error"
        result["message"] = f"获取服务器列表失败: {err}"
        return result

    servers = server_data.get("data", [])
    if not servers:
        print(f"[INFO]   无服务器")
        result["status"] = "no_servers"
        result["message"] = "账号下无服务器"
        return result

    print(f"[INFO]   发现 {len(servers)} 个服务器")

    # [步骤3] 逐个处理服务器
    print(f"[INFO] [步骤3] 逐个查询服务器详情并续期...")
    for idx, srv in enumerate(servers, 1):
        srv_id = srv.get("identifier", "unknown")
        srv_uuid = srv.get("uuid", "")
        srv_name = srv.get("name", "")
        srv_type = srv.get("server_type", "free")  # free 或 notfree
        srv_attrs = srv.get("attributes", srv)

        print(f"\n  {'─' * 50}")
        print(f"  [INFO] 服务器 {idx}/{len(servers)}: {mask_text(srv_id, 2)} [{srv_type}] {srv_name}")

        # 查询服务器详情（含到期时间）
        if srv_uuid:
            ep = f"/freeservers/{srv_uuid}/info" if srv_type == "free" else f"/notfreeservers/{srv_uuid}/info"
            info = api_get(session, f"{API_BASE}{ep}", xsrf_token)
            if info and info.get("success"):
                expire = info.get("data", {}).get("expire", "Unknown")
                print(f"  [INFO] 当前到期: {expire}")

                # 检查是否需要续期（剩余 < 24 小时）
                try:
                    exp_dt = datetime.strptime(expire.split(".")[0], "%Y-%m-%d %H:%M:%S")
                    remaining = (exp_dt - datetime.now()).total_seconds() / 3600
                    if remaining > 24:
                        print(f"  [INFO] 剩余 {remaining:.1f} 小时，跳过续期")
                        result["servers"].append({
                            "id": srv_id,
                            "name": srv_name,
                            "type": srv_type,
                            "expire": expire,
                            "status": "skipped",
                            "message": f"剩余 {remaining:.1f}h",
                        })
                        continue
                except Exception:
                    pass

        # 尝试续期 API
        print(f"  [INFO] 尝试调用续期 API...")

        # 已知的 Weirdhost 续期 API 端点（基于网页行为推测）
        # 实际端点可能需要从网页 JS 抓取
        renew_endpoints = [
            f"{API_BASE}/freeservers/{srv_uuid}/renew" if srv_type == "free" else f"{API_BASE}/notfreeservers/{srv_uuid}/renew",
            f"{API_BASE}/freeservers/{srv_uuid}/extend" if srv_type == "free" else f"{API_BASE}/notfreeservers/{srv_uuid}/extend",
            f"{API_BASE}/freeservers/{srv_uuid}/addtime" if srv_type == "free" else f"{API_BASE}/notfreeservers/{srv_uuid}/addtime",
        ]

        renew_ok = False
        for ep in renew_endpoints:
            r = api_post(session, ep, data={}, xsrf_token=xsrf_token)
            if r and not r.get("_error"):
                if r.get("success"):
                    new_expire = r.get("data", {}).get("expire", "Unknown")
                    print(f"  [INFO] ✅ 续期成功！新到期: {new_expire}")
                    result["servers"].append({
                        "id": srv_id,
                        "name": srv_name,
                        "type": srv_type,
                        "expire": new_expire,
                        "status": "success",
                        "message": f"续期成功",
                    })
                    renew_ok = True
                    break
                elif "turnstile" in str(r).lower() or "captcha" in str(r).lower():
                    print(f"  [WARN] API 需要 Turnstile 验证: {r}")
                    break  # 跳出循环，不尝试其他端点
                elif "cooldown" in str(r).lower() or "아직" in str(r):
                    print(f"  [INFO] 冷却期内")
                    result["servers"].append({
                        "id": srv_id,
                        "name": srv_name,
                        "type": srv_type,
                        "expire": expire if 'expire' in dir() else "Unknown",
                        "status": "cooldown",
                        "message": "冷却期内",
                    })
                    renew_ok = True
                    break
            time.sleep(0.5)

        if not renew_ok:
            print(f"  [WARN] API 直连续期失败，可能需要 Turnstile")
            result["servers"].append({
                "id": srv_id,
                "name": srv_name,
                "type": srv_type,
                "expire": expire if 'expire' in dir() else "Unknown",
                "status": "needs_turnstile",
                "message": "需要 Turnstile 验证",
            })

        # 防止请求过快
        time.sleep(random.uniform(1.0, 2.0))

    # 汇总
    success_count = sum(1 for s in result["servers"] if s["status"] == "success")
    skipped_count = sum(1 for s in result["servers"] if s["status"] == "skipped")
    needs_turnstile_count = sum(1 for s in result["servers"] if s["status"] == "needs_turnstile")

    if success_count > 0:
        result["status"] = "success"
        result["message"] = f"{success_count} 个服务器续期成功"
    elif needs_turnstile_count > 0:
        result["status"] = "needs_turnstile"
        result["message"] = f"{needs_turnstile_count} 个服务器需要 Turnstile"
    else:
        result["status"] = "skipped"
        result["message"] = f"{skipped_count} 个服务器跳过"

    return result


def send_telegram(result):
    """发送 Telegram 通知"""
    tg_token = os.environ.get("TG_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TG_CHAT_ID", "").strip()
    if not tg_token or not tg_chat:
        return

    status_emoji = {
        "success": "🟢",
        "needs_turnstile": "🟡",
        "skipped": "⚪",
        "error": "🔴",
        "cf_blocked": "🛡️",
        "cookie_invalid": "🍪",
        "no_servers": "➖",
    }.get(result["status"], "❓")

    msg = (
        f"{status_emoji} <b>Weirdhost 续期</b>\n\n"
        f"账号: <code>{mask_text(result['remark'])}</code>\n"
        f"状态: {result['status']}\n"
        f"详情: {result['message']}\n"
    )
    if result.get("servers"):
        msg += "\n<b>服务器:</b>\n"
        for s in result["servers"]:
            emoji = {"success": "✅", "skipped": "⏭️", "needs_turnstile": "⚠️", "cooldown": "❄️"}.get(s["status"], "❓")
            msg += f"{emoji} {s['name']} [{s['type']}] → {s['expire']} ({s['status']})\n"

    try:
        requests.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            data={"chat_id": tg_chat, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
        print(f"[INFO] Telegram 通知已发送")
    except Exception as e:
        print(f"[WARN] Telegram 通知失败: {e}")


def main():
    print("=" * 60)
    print("  Weirdhost Auto Renew (API 直连版)")
    print("=" * 60)

    accounts = detect_accounts()
    if not accounts:
        print("[ERROR] 未检测到任何账号，请检查 WEIRDHOST_COOKIE_N 环境变量")
        sys.exit(1)

    print(f"\n[INFO] 共 {len(accounts)} 个账号待续期\n")

    session = make_session()
    results = []
    for i, acc in enumerate(accounts):
        if i > 0:
            wait = random.randint(3, 6)
            print(f"\n[INFO] 等待 {wait}s 后处理下一个账号...")
            time.sleep(wait)
        result = renew_account(session, acc)
        results.append(result)
        send_telegram(result)

    # 汇总
    print("\n" + "=" * 60)
    print("[INFO] 续期汇总")
    print("=" * 60)
    for r in results:
        emoji = {
            "success": "✅",
            "needs_turnstile": "⚠️",
            "skipped": "⏭️",
            "error": "❌",
            "cf_blocked": "🛡️",
            "cookie_invalid": "🍪",
            "no_servers": "➖",
        }.get(r["status"], "❓")
        print(f"{emoji} {mask_text(r['remark'])} | {r['message']}")

    # 退出码
    has_error = any(r["status"] in ("error", "cf_blocked", "cookie_invalid") for r in results)
    sys.exit(1 if has_error else 0)


if __name__ == "__main__":
    main()
