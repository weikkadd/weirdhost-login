#!/bin/bash
# 启动 sing-box 把 hysteria2/vless/vmess/trojan 等协议转成本地 SOCKS5
# 用法：在 GHA 里 source 这个脚本，或者直接 bash 运行
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
echo "sing-box ready: $("$SINGBOX_BIN" version | head -1)"

echo "=== 2. 解析 PROXY_NODE ==="
PROTO=$(echo "$PROXY_NODE" | sed -E 's|^([a-z0-9]+)://.*|\1|')
echo "protocol: $PROTO"

mkdir -p /tmp/sing-box
CONFIG_FILE="/tmp/sing-box/config.json"

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
nohup "$SINGBOX_BIN" run -c "$CONFIG_FILE" > /tmp/singbox.log 2>&1 &
SINGBOX_PID=$!
echo "sing-box started (PID=$SINGBOX_PID)"
sleep 3
if kill -0 $SINGBOX_PID 2>/dev/null; then
  echo "sing-box alive"
else
  echo "sing-box failed to start"
  cat /tmp/singbox.log
  exit 1
fi

echo "=== 4. 验证代理出网 ==="
for i in 1 2 3 4 5; do
  if curl -s --socks5 127.0.0.1:1080 --max-time 10 "https://ipinfo.io/json" > /tmp/ipinfo.json 2>&1; then
    cat /tmp/ipinfo.json | jq .
    echo "proxy working"
    break
  fi
  echo "waiting for sing-box... ($i/5)"
  sleep 2
done

if [ ! -s /tmp/ipinfo.json ]; then
  echo "proxy verification failed"
  cat /tmp/singbox.log
  exit 1
fi
