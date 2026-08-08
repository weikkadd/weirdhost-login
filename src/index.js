/**
 * PellaFree - Microsoft 365 E5 Developer Program Auto Renewal Worker
 * 
 * 通过 Cloudflare Workers 调用 Microsoft Graph API 保持开发者订阅活跃
 */

const CONFIG = {
  // Microsoft Graph API 端点
  GRAPH_API: 'https://graph.microsoft.com',
  
  // 续期检查间隔（毫秒）- 建议设置为 88 天
  RENEW_INTERVAL: 88 * 24 * 60 * 60 * 1000,
  
  // User-Agent
  USER_AGENT: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
};

/**
 * Worker 入口函数
 */
export default {
  /**
   * 处理 HTTP 请求
   */
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // CORS 头
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    };
    
    if (request.method === 'OPTIONS') {
      return new Response(JSON.stringify({ status: 'ok' }), { headers });
    }
    
    // 续期端点
    if (url.pathname === '/renew' && request.method === 'POST') {
      return await handleRenew(request, env, headers);
    }
    
    // 健康检查
    if (url.pathname === '/health') {
      return new Response(JSON.stringify({ 
        status: 'healthy',
        timestamp: new Date().toISOString()
      }), { headers });
    }
    
    // 默认响应
    return new Response(JSON.stringify({ 
      message: 'PellaFree Worker',
      endpoints: ['/renew', '/health']
    }), { headers });
  }
};

/**
 * 处理续期请求
 */
async function handleRenew(request, env, headers) {
  try {
    // 获取授权 token
    const token = request.headers.get('Authorization')?.replace('Bearer ', '');
    
    if (!token || token !== env.CF_API_TOKEN) {
      return new Response(JSON.stringify({ 
        success: false, 
        message: 'Unauthorized' 
      }), { 
        status: 401, 
        headers 
      });
    }
    
    // 调用 Microsoft Graph API 保持活跃
    const result = await callMicrosoftGraph(env);
    
    // 发送 Telegram 通知（可选）
    if (env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID) {
      await sendTelegramNotification(env, result);
    }
    
    return new Response(JSON.stringify({
      success: true,
      message: 'Renewal check completed',
      ...result
    }), { headers });
    
  } catch (error) {
    console.error('Renewal error:', error);
    
    // 发送错误通知
    if (env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID) {
      await sendTelegramNotification(env, { error: error.message });
    }
    
    return new Response(JSON.stringify({
      success: false,
      message: error.message
    }), { 
      status: 500, 
      headers 
    });
  }
}

/**
 * 调用 Microsoft Graph API
 */
async function callMicrosoftGraph(env) {
  const startTime = Date.now();
  
  // 尝试调用多个 API 端点来保持活跃
  const endpoints = [
    'https://graph.microsoft.com/v1.0/me',
    'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=1',
    'https://graph.microsoft.com/v1.0/me/calendar/events?$top=1'
  ];
  
  const results = [];
  
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${env.MS_ACCESS_TOKEN}`,
          'User-Agent': CONFIG.USER_AGENT
        }
      });
      
      results.push({
        endpoint,
        status: response.status,
        success: response.ok
      });
      
      // 随机延迟，模拟人工操作
      await sleep(Math.random() * 1000 + 500);
      
    } catch (error) {
      results.push({
        endpoint,
        status: 0,
        success: false,
        error: error.message
      });
    }
  }
  
  const duration = Date.now() - startTime;
  
  return {
    results,
    duration: `${duration}ms`,
    checkedAt: new Date().toISOString()
  };
}

/**
 * 发送 Telegram 通知
 */
async function sendTelegramNotification(env, result) {
  const message = `🤖 PellaFree Renewal Report\n\n` +
    `时间: ${result.checkedAt || new Date().toISOString()}\n` +
    `状态: ${result.success ? '✅ 成功' : '❌ 失败'}\n` +
    `详情: ${JSON.stringify(result)}`;
  
  try {
    await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: env.TELEGRAM_CHAT_ID,
        text: message,
        parse_mode: 'HTML'
      })
    });
  } catch (error) {
    console.error('Telegram notification failed:', error);
  }
}

/**
 * 延迟函数
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
