#!/usr/bin/env python3
"""
Weirdhost 自动续期脚本
支持多账号管理
"""

import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path

# 配置
WEIRDHOST_URL = os.getenv('WEIRDHOST_URL', 'https://weirdhost.net')
LOG_FILE = Path(__file__).parent / 'logs' / 'renew.log'


def load_accounts():
    """加载账号配置"""
    accounts_json = os.getenv('WEIRDHOST_ACCOUNTS', '[]')
    try:
        accounts = json.loads(accounts_json)
    except json.JSONDecodeError:
        accounts = []
    return accounts


def check_cookie_validity(cookie):
    """检查 Cookie 是否有效"""
    try:
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(
            f'{WEIRDHOST_URL}/dashboard',
            headers=headers,
            timeout=30
        )
        
        return response.status_code == 200
    except Exception as e:
        log(f'检查 Cookie 失败: {e}')
        return False


def renew_session(cookie):
    """续期会话"""
    try:
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }
        
        # 访问续期端点
        response = requests.post(
            f'{WEIRDHOST_URL}/login/check',
            headers=headers,
            json={},
            timeout=30
        )
        
        if response.status_code == 200:
            log('会话续期成功')
            return True
        else:
            log(f'会话续期失败: HTTP {response.status_code}')
            return False
            
    except Exception as e:
        log(f'续期过程中出错: {e}')
        return False


def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f'[{timestamp}] {message}'
    print(log_message)
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')


def main():
    """主函数"""
    log('开始执行 Weirdhost 自动续期')
    
    accounts = load_accounts()
    
    if not accounts:
        log('未找到账号配置，跳过续期')
        return
    
    success_count = 0
    fail_count = 0
    
    for i, account in enumerate(accounts, 1):
        cookie = account.get('cookie')
        name = account.get('name', f'账号{i}')
        url = account.get('url', WEIRDHOST_URL)
        
        log(f'处理 {name}...')
        
        if not cookie:
            log(f'{name}: 缺少 Cookie，跳过')
            fail_count += 1
            continue
        
        # 检查会话状态
        if not check_cookie_validity(cookie):
            log(f'{name}: Cookie 已过期')
            fail_count += 1
            continue
        
        # 续期会话
        if renew_session(cookie):
            success_count += 1
            log(f'{name}: 续期成功')
        else:
            fail_count += 1
            log(f'{name}: 续期失败')
        
        # 随机延迟，模拟人工操作
        time.sleep(3 + (i % 5))
    
    log(f'执行完成: 成功 {success_count} 个，失败 {fail_count} 个')


if __name__ == '__main__':
    main()
