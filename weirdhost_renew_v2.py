#!/usr/bin/env python3
"""
Weirdhost 自动续期脚本 v2 - 修复 Cloudflare Turnstile 问题
"""

import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

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


class WeirdhostRenewer:
    """Weirdhost 自动续期器"""
    
    def __init__(self, cookie, proxy=None, telegram_bot_token=None, telegram_chat_id=None):
        self.cookie = cookie
        self.proxy = proxy
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.weirdhost_url = "https://hub.weirdhost.xyz"
        self.driver = None
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)
    
    def setup_driver(self):
        """配置 Chrome 驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 反检测选项
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 代理设置
        if self.proxy:
            chrome_options.add_argument(f'--proxy-server={self.proxy}')
        
        # 用户代理
        chrome_options.add_argument(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 执行 CDP 命令注入反检测脚本
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    window.chrome = { runtime: {} };
                '''
            })
            
            logger.info("浏览器驱动配置完成")
            return True
        except Exception as e:
            logger.error(f"浏览器驱动配置失败: {e}")
            return False
    
    def inject_cf_clearance(self):
        """注入 CF_CLEARANCE cookie"""
        cf_clearance = os.getenv('CF_CLEARANCE', '')
        if cf_clearance:
            logger.info(f"注入 CF_CLEARANCE cookie (长度: {len(cf_clearance)})")
            self.driver.add_cookie({
                'name': 'cf_clearance',
                'value': cf_clearance,
                'domain': 'hub.weirdhost.xyz',
                'path': '/'
            })
    
    def inject_remember_web_cookie(self):
        """注入 remember_web Cookie"""
        if self.cookie:
            logger.info(f"注入 remember_web Cookie")
            self.driver.add_cookie({
                'name': 'remember_web',
                'value': self.cookie,
                'domain': 'hub.weirdhost.xyz',
                'path': '/'
            })
    
    def handle_cloudflare_turnstile(self, max_attempts=10):
        """处理 Cloudflare Turnstile 验证"""
        logger.info("开始处理 Cloudflare Turnstile...")
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"CF 处理尝试 {attempt}/{max_attempts}...")
            
            try:
                # 等待 Turnstile 容器出现
                turnstile_selector = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[name="cfturnstile"], .cf-turnstile'))
                )
                
                logger.info("检测到 Turnstile 验证框")
                
                # 尝试注入 Turnstile 绕过脚本
                self.driver.execute_script('''
                    // 尝试自动完成 Turnstile
                    const turnstile = document.querySelector('[name="cfturnstile"]');
                    if (turnstile) {
                        // 尝试触发 Turnstile 回调
                        const callback = turnstile.closest('form')?.dataset['callback'] || 
                                         window.location.hash?.split('=')[1];
                        if (callback) {
                            window[callback]?.('bypassed-token');
                        }
                    }
                ''')
                
                # 等待页面重定向
                time.sleep(3)
                
                # 检查是否成功通过
                current_url = self.driver.current_url
                if 'hub.weirdhost.xyz' in current_url and 'challenge' not in current_url:
                    logger.info(f"CF 验证通过！当前 URL: {current_url}")
                    return True
                    
            except TimeoutException:
                logger.info("Turnstile 容器未找到，可能已过期")
                break
            except Exception as e:
                logger.warning(f"CF 处理异常: {e}")
        
        logger.error("CF 验证失败，已达到最大尝试次数")
        return False
    
    def check_account_status(self):
        """检查账号状态"""
        logger.info("=" * 60)
        logger.info("检查账号状态...")
        logger.info("=" * 60)
        
        if not self.setup_driver():
            logger.error("浏览器驱动配置失败")
            return False
        
        try:
            # 注入 Cookies
            self.inject_remember_web_cookie()
            self.inject_cf_clearance()
            
            # 访问站点
            logger.info(f"访问 {self.weirdhost_url}...")
            self.driver.get(self.weirdhost_url)
            time.sleep(5)
            
            # 处理 CF 挑战
            if not self.handle_cloudflare_turnstile():
                logger.error("Cloudflare 验证失败")
                self.save_debug_artifacts("cf_failed")
                return False
            
            # 等待页面加载
            time.sleep(3)
            
            # 检查是否成功登录
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            if 'dashboard' in current_url or '账户' in page_source or '我的' in page_source:
                logger.info("✅ 登录成功，账号状态正常")
                self.save_debug_artifacts("success")
                return True
            else:
                logger.warning(f"⚠️  页面状态异常，当前 URL: {current_url}")
                self.save_debug_artifacts("status_check")
                return False
                
        except Exception as e:
            logger.error(f"检查账号状态时出错: {e}")
            self.save_debug_artifacts("error")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def renew_session(self):
        """续期会话"""
        logger.info("=" * 60)
        logger.info("执行会话续期...")
        logger.info("=" * 60)
        
        if not self.setup_driver():
            logger.error("浏览器驱动配置失败")
            return False
        
        try:
            # 注入 Cookies
            self.inject_remember_web_cookie()
            self.inject_cf_clearance()
            
            # 访问续期端点
            renew_url = f"{self.weirdhost_url}/login/check"
            logger.info(f"访问续期端点: {renew_url}")
            self.driver.get(renew_url)
            time.sleep(5)
            
            # 检查续期结果
            current_url = self.driver.current_url
            status = "success" if 'dashboard' in current_url or '账户' in self.driver.page_source else "failed"
            
            if status == "success":
                logger.info("✅ 会话续期成功")
                self.send_telegram_notification("✅ 续期成功", current_url)
            else:
                logger.error("❌ 会话续期失败")
                self.send_telegram_notification("❌ 续期失败", current_url)
                self.save_debug_artifacts("renew_failed")
            
            return status == "success"
            
        except Exception as e:
            logger.error(f"续期会话时出错: {e}")
            self.send_telegram_notification(f"❌ 续期出错: {str(e)[:100]}", "")
            self.save_debug_artifacts("renew_error")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_debug_artifacts(self, prefix):
        """保存调试信息"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{timestamp}"
        
        # 截图
        screenshot_path = self.screenshots_dir / f"{filename}.png"
        self.driver.save_screenshot(screenshot_path)
        logger.info(f"截图已保存: {screenshot_path}")
        
        # HTML
        html_path = self.screenshots_dir / f"{filename}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        logger.info(f"HTML 已保存: {html_path}")
    
    def send_telegram_notification(self, message, url=""):
        """发送 Telegram 通知"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return
        
        try:
            text = f"{message}\n\nURL: {url}" if url else message
            response = requests.post(
                f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage",
                json={
                    'chat_id': self.telegram_chat_id,
                    'text': text,
                    'parse_mode': 'HTML'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Telegram 通知发送成功")
            else:
                logger.warning(f"Telegram 通知发送失败: {response.text}")
                
        except Exception as e:
            logger.warning(f"发送 Telegram 通知时出错: {e}")
    
    def run(self):
        """运行续期流程"""
        logger.info("=" * 60)
        logger.info("开始 Weirdhost 自动续期")
        logger.info("=" * 60)
        
        # 检查账号状态
        if not self.check_account_status():
            logger.warning("账号状态检查失败，尝试直接续期...")
        
        # 执行续期
        success = self.renew_session()
        
        logger.info("=" * 60)
        if success:
            logger.info("✅ 续期流程完成")
        else:
            logger.error("❌ 续期流程失败")
        logger.info("=" * 60)
        
        return success


def main():
    parser = argparse.ArgumentParser(description='Weirdhost 自动续期脚本')
    parser.add_argument('--cookie', required=True, help='remember_web Cookie')
    parser.add_argument('--proxy', help='代理地址 (如 socks5://127.0.0.1:1080)')
    parser.add_argument('--telegram-bot', help='Telegram Bot Token')
    parser.add_argument('--telegram-chat', help='Telegram Chat ID')
    
    args = parser.parse_args()
    
    renewer = WeirdhostRenewer(
        cookie=args.cookie,
        proxy=args.proxy,
        telegram_bot_token=args.telegram_bot,
        telegram_chat_id=args.telegram_chat
    )
    
    success = renewer.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
