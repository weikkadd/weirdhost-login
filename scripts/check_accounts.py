#!/usr/bin/env python3
"""
账号状态检查脚本
"""

import os
import json
import requests
from datetime import datetime


def load_accounts():
    """加载账号配置"""
    accounts_json = os.getenv('WEIRDHOST_ACCOUNTS', '[]')
    try:
        accounts = json.loads(accounts_json)
    except json.JSONDecodeError:
        print("❌ JSON 解析失败")
        return []
    return accounts


def check_account_status(cookie):
    """检查单个账号状态"""
    try:
        headers = {
            'Cookie': cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(
            'https://weirdhost.net/dashboard',
            headers=headers,
            timeout=30
        )
        
        return {
            'status_code': response.status_code,
            'valid': response.status_code == 200,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'status_code': 0,
            'valid': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def main():
    """主函数"""
    print(f"\n🔍 开始检查账号状态 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    accounts = load_accounts()
    
    if not accounts:
        print("❌ 未找到账号配置")
        return
    
    total = len(accounts)
    valid_count = 0
    invalid_count = 0
    
    for i, account in enumerate(accounts, 1):
        name = account.get('name', f'账号{i}')
        cookie = account.get('cookie', '')
        
        print(f"[{i}/{total}] 检查 {name}...")
        
        if not cookie:
            print(f"  ❌ 缺少 Cookie\n")
            invalid_count += 1
            continue
        
        result = check_account_status(cookie)
        
        if result['valid']:
            print(f"  ✅ Cookie 有效 (HTTP {result['status_code']})\n")
            valid_count += 1
        else:
            print(f"  ❌ Cookie 无效 (HTTP {result['status_code']})\n")
            invalid_count += 1
    
    print("=" * 50)
    print(f"📊 检查结果:")
    print(f"  总计: {total} 个账号")
    print(f"  有效: {valid_count} 个")
    print(f"  无效: {invalid_count} 个")
    print("=" * 50 + "\n")


if __name__ == '__main__':
    main()
