#!/usr/bin/env python3
"""
Weirdhost 自动续期脚本 - 纯 API 版本（无需浏览器）
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime

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
    """Weirdhost 自动续期器 - 纯 API 版本"""
    
    def __init__(self, cookie, url=None, proxy=None):
        self.cookie = cookie
        self.url = url or 'https://hub.weirdhost.xyz'
        self.proxy = proxy
        self.session = requests.Session()
        
        # 配置代理
        if proxy:
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cookie': cookie
        })
    
    def check_session_valid(self):
        """检查会话是否有效"""
        try:
            response = self.session.get(
                f'{self.url}/dashboard',
                timeout=30,
                allow_redirects=True
            )
            
            # 检查是否重定向到登录页
            if 'login' in response.url.lower():
                logger.warning("会话已过期，需要重新登录")
                return False
            
            # 检查响应状态
            if response.status_code == 200:
                logger.info(f"会话有效，当前 URL: {response.url}")
                return True
            else:
                logger.warning(f"会话状态异常: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"检查会话时出错: {e}")
            return False
    
    def renew_session(self):
        """续期会话"""
        logger.info("=" * 60)
        logger.info("执行会话续期...")
        logger.info("=" * 60)
        
        try:
            # 方法 1: 尝试访问续期端点
            logger.info("方法 1: 访问 /login/check 端点")
            response = self.session.post(
                f'{self.url}/login/check',
                json={},
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"响应状态: {response.status_code}")
            logger.info(f"响应 URL: {response.url}")
            
            # 检查是否成功
            if 'dashboard' in response.url or response.status_code == 200:
                logger.info("✅ 方法 1 成功")
                return True
            
            # 方法 2: 访问任意页面刷新会话
            logger.info("方法 2: 访问仪表盘页面")
            response = self.session.get(
                f'{self.url}/dashboard',
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"响应状态: {response.status_code}")
            logger.info(f"响应 URL: {response.url}")
            
            if 'login' not in response.url.lower():
                logger.info("✅ 方法 2 成功")
                return True
            
            # 方法 3: 尝试刷新页面
            logger.info("方法 3: 刷新首页")
            response = self.session.get(
                self.url,
                timeout=30,
                allow_redirects=True
            )
            
            logger.info(f"响应状态: {response.status_code}")
            logger.info(f"响应 URL: {response.url}")
            
            if 'login' not in response.url.lower():
                logger.info("✅ 方法 3 成功")
                return True
            
            logger.error("❌ 所有方法都失败，会话可能已过期")
            return False
            
        except Exception as e:
            logger.error(f"续期会话时出错: {e}")
            return False
    
    def run(self):
        """运行续期流程"""
        logger.info("=" * 60)
        logger.info("开始 Weirdhost 自动续期 (API 版本)")
        logger.info("=" * 60)
        
        # 检查会话状态
        if not self.check_session_valid():
            logger.warning("会话已过期，无法续期")
            return False
        
        # 执行续期
        success = self.renew_session()
        
        # 随机延迟，模拟人工操作
        time.sleep(2 + hash(self.cookie) % 3)
        
        logger.info("=" * 60)
        if success:
            logger.info("✅ 续期流程完成")
        else:
            logger.error("❌ 续期流程失败")
        logger.info("=" * 60)
        
        return success


def main():
    parser = argparse.ArgumentParser(description='Weirdhost 自动续期脚本 (API 版本)')
    parser.add_argument('--cookie', required=True, help='remember_web Cookie')
    parser.add_argument('--url', help='Weirdhost 网站 URL')
    parser.add_argument('--proxy', help='代理地址 (如 socks5://127.0.0.1:1080)')
    
    args = parser.parse_args()
    
    renewer = WeirdhostRenewer(
        cookie=args.cookie,
        url=args.url,
        proxy=args.proxy
    )
    
    success = renewer.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    import argparse
    main()
