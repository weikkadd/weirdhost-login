#!/bin/bash
# 启动 sing-box 把 hysteria2/vless/vmess/trojan 等协议转成本地 SOCKS5
# 关键修复：用 setsid + disown 让 sing-box 真正脱离 GHA step 进程
# 这样即使 step 完成，sing-box 进程也不会被杀
set -e

PROXY_NODE="${PROXY_NODE:-}"
if [ -z "$PROXY_NODE" ]; then
  echo "[ERROR] PROXY_NODE 环境变量为空"
  exit 1
fi

echo "=== 1. 下载 sing-box ==="
SINGBOX_VERSION="1.13.16"
wget -q "https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz" -O /tmp/singbox.tgz
tar xzf /tmp/singbox.tgz -C /tmp
SINGBOX_BIN=$(find /tmp -name "sing-box" -type f | head -1)
chmod +x "$SINGBOX_BIN"
# 把 sing-box 二进制复制到稳定路径，避免被 GHA 清理
cp "$SINGBOX_BIN" /usr/local/bin/sing-box
SINGBOX_BIN=/usr/local/bin/sing-box
chmod +x "$SINGBOX_BIN"
echo "sing-box ready: $("$SINGBOX_BIN" version | head -1)"

echo "=== 2. 解析 PROXY_NODE ==="
PROTO=$(echo "$PROXY_NODE" | sed -E 's|^([a-z0-9]+)://.*|\1|')
echo "protocol: $PROTO"

# 配置文件放 /etc，避免被 GHA /tmp 清理
mkdir -p /etc/sing-box
CONFIG_FILE="/etc/sing-box/config.json"

case "$PROTO" in
  hysteria2|hy2)
    AUTH=$(echo "$PROXY_NODE" | sed -E 's|^[a-z0-9]+://([^@]+)@.*|\1|' | sed 's|%3A|:|g')
    HOST_PORT=$(echo "$PROXY_NODE" | sed -E 's|^[a-z0-9]+://[^@]+@([^/?]+).*|\1|')
    HOST=$(echo "$HOST_PORT" | cut -d: -f1)
    PORT=$(echo "$HOST_PORT" | cut -d: -f2)
    SNI=$(echo "$PROXY_NODE" | grep -oE 'sni=[^&]+' | cut -d= -f2 | head -1)
    if [ -z "$SNI" ]; then SNI="$HOST"; fi
    INSECURE=$(echo "$PROXY_NODE" | grep -oE 'insecure=[0-9]' | cut -d= -f2 | head -1)
    if [ -z "$INSECURE" ]; then INSECURE=0; fi
    if [ "$INSECURE" = "1" ]; then INSECURE_BOOL=true; else INSECURE_BOOL=false; fi

    cat > "$CONFIG_FILE" <<EOF
{
  "log": {"level": "info"},
  "inbounds": [
    {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 1080},
    {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 1081}
  ],
  "outbounds": [
    {
      "type": "hysteria2",
      "tag": "proxy",
      "server": "$HOST",
      "server_port": $PORT,
      "password": "$AUTH",
      "tls": {
        "enabled": true,
        "server_name": "$SNI",
        "insecure": $INSECURE_BOOL
      }
    }
  ]
}
EOF
    ;;
  *)
    echo "Unsupported protocol: $PROTO"
    echo "Supported: hysteria2/hy2"
    exit 1
    ;;
esac

echo "server: $HOST:$PORT"
echo "config generated:"
cat "$CONFIG_FILE" | jq .

echo "=== 3. 启动 sing-box（后台） ==="
# 关键修复：用 setsid 创建新会话 + disown 让进程脱离当前 shell
# 这样 GHA step 完成后 sing-box 不会被杀
LOG_FILE="/tmp/singbox.log"
setsid nohup "$SINGBOX_BIN" run -c "$CONFIG_FILE" > "$LOG_FILE" 2>&1 < /dev/null &
SINGBOX_PID=$!
disown $SINGBOX_PID 2>/dev/null || true
echo "sing-box started (PID=$SINGBOX_PID, PGID=$(ps -o pgid= -p $SINGBOX_PID 2>/dev/null | tr -d ' '))"

# 等待启动并验证存活
sleep 3
if kill -0 $SINGBOX_PID 2>/dev/null; then
  echo "sing-box alive after 3s"
else
  echo "sing-box failed to start"
  cat "$LOG_FILE"
  exit 1
fi

# 再等几秒确认进程稳定
sleep 5
if kill -0 $SINGBOX_PID 2>/dev/null; then
  echo "sing-box alive after 8s"
else
  echo "sing-box died after 8s"
  cat "$LOG_FILE"
  exit 1
fi

echo "=== 4. 验证代理出网 ==="
for i in 1 2 3 4 5; do
  if curl -s --socks5 127.0.0.1:1080 --max-time 10 "https://ipinfo.io/json" > /tmp/ipinfo.json 2>&1; then
    if jq -e .ip /tmp/ipinfo.json > /dev/null 2>&1; then
      cat /tmp/ipinfo.json | jq .
      echo "proxy working"
      break
    fi
  fi
  echo "waiting for sing-box... ($i/5)"
  sleep 2
  # 检查 sing-box 是否还活着
  if ! kill -0 $SINGBOX_PID 2>/dev/null; then
    echo "sing-box died during verification!"
    cat "$LOG_FILE"
    exit 1
  fi
done

if [ ! -s /tmp/ipinfo.json ] || ! jq -e .ip /tmp/ipinfo.json > /dev/null 2>&1; then
  echo "proxy verification failed"
  cat "$LOG_FILE"
  exit 1
fi

# 保存 PID 给后续 step 用
echo "$SINGBOX_PID" > /tmp/singbox.pid
echo "sing-box PID saved to /tmp/singbox.pid"
