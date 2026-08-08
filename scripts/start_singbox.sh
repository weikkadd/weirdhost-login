#!/bin/bash
# 启动 sing-box 把 hysteria2/vless/vmess/trojan/ss 等协议转成本地 SOCKS5
# 支持协议：hysteria2/hy2, vless (TLS/REALITY + TCP/WS/gRPC), vmess, trojan, shadowsocks
# 关键修复：用 setsid + disown 让 sing-box 真正脱离 GHA step 进程

PROXY_NODE="${PROXY_NODE:-}"
if [ -z "$PROXY_NODE" ]; then
  echo "[ERROR] PROXY_NODE 环境变量为空"
  exit 1
fi

# 如果已经有 sing-box 在跑，先杀掉
EXISTING_PIDS=$(pgrep -f "sing-box run" 2>/dev/null || true)
if [ -n "$EXISTING_PIDS" ]; then
  echo "[INFO] 发现已存在的 sing-box 进程 (PID: $EXISTING_PIDS)，杀掉..."
  pkill -9 -f "sing-box run" 2>/dev/null || true
  sleep 2
fi

echo "=== 1. 下载 sing-box ==="
SINGBOX_VERSION="1.13.16"
if [ -x "/usr/local/bin/sing-box" ]; then
  SINGBOX_BIN=/usr/local/bin/sing-box
  echo "sing-box already installed: $("$SINGBOX_BIN" version | head -1)"
else
  wget -q "https://github.com/SagerNet/sing-box/releases/download/v${SINGBOX_VERSION}/sing-box-${SINGBOX_VERSION}-linux-amd64.tar.gz" -O /tmp/singbox.tgz
  tar xzf /tmp/singbox.tgz -C /tmp
  SINGBOX_BIN_TMP=$(find /tmp -maxdepth 3 -name "sing-box" -type f 2>/dev/null | head -1)
  chmod +x "$SINGBOX_BIN_TMP"
  cp "$SINGBOX_BIN_TMP" /usr/local/bin/sing-box
  SINGBOX_BIN=/usr/local/bin/sing-box
  chmod +x "$SINGBOX_BIN"
  echo "sing-box installed: $("$SINGBOX_BIN" version | head -1)"
fi

echo "=== 2. 解析 PROXY_NODE ==="
# 先剥离 #remark 部分（URL fragment），避免污染参数
PROXY_NODE_CLEAN=$(echo "$PROXY_NODE" | sed -E 's|#.*$||')
echo "url (without fragment): $PROXY_NODE_CLEAN"

PROTO=$(echo "$PROXY_NODE_CLEAN" | sed -E 's|^([a-z0-9]+)://.*|\1|')
echo "protocol: $PROTO"

mkdir -p /tmp/sing-box
CONFIG_FILE="/tmp/sing-box/config.json"
PROXY_NODE_CLEAN_ARG="$PROXY_NODE_CLEAN"

# ============================================================
# 通用：URL 参数提取函数
# 用法: get_param "url" "param_name" "default_value"
# ============================================================
get_param() {
  local url="$1"
  local key="$2"
  local default="${3:-}"
  local val
  val=$(echo "$url" | grep -oE "${key}=[^&]*" | head -1 | cut -d= -f2-)
  # URL decode 常见字符
  val="${val//%2F/\/}"
  val="${val//%3D/=}"
  val="${val//%3A/:}"
  val="${val//%3F/?}"
  val="${val//%3B/;}"
  val="${val//%20/ }"
  val="${val//%2B/+}"
  val="${val//%2C/,}"
  if [ -z "$val" ]; then
    echo "$default"
  else
    echo "$val"
  fi
}

case "$PROTO" in
  # ============================================================
  # HYSTERIA2 / HY2
  # ============================================================
  hysteria2|hy2)
    AUTH=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^[a-z0-9]+://([^@]+)@.*|\1|' | sed 's|%3A|:|g')
    HOST_PORT=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^[a-z0-9]+://[^@]+@([^/?]+).*|\1|')
    HOST=$(echo "$HOST_PORT" | cut -d: -f1)
    PORT=$(echo "$HOST_PORT" | cut -d: -f2)
    SNI=$(get_param "$PROXY_NODE_CLEAN_ARG" "sni" "$HOST")
    INSECURE=$(get_param "$PROXY_NODE_CLEAN_ARG" "insecure" "0")
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

  # ============================================================
  # VLESS (支持 TLS / REALITY + TCP / WS / gRPC)
  # ============================================================
  vless)
    UUID=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^vless://([^@]+)@.*|\1|')
    HOST_PORT=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^vless://[^@]+@([^/?]+).*|\1|')
    HOST=$(echo "$HOST_PORT" | cut -d: -f1)
    PORT=$(echo "$HOST_PORT" | cut -d: -f2)
    SECURITY=$(get_param "$PROXY_NODE_CLEAN_ARG" "security" "none")
    SNI=$(get_param "$PROXY_NODE_CLEAN_ARG" "sni" "$HOST")
    TYPE=$(get_param "$PROXY_NODE_CLEAN_ARG" "type" "tcp")
    FLOW=$(get_param "$PROXY_NODE_CLEAN_ARG" "flow" "")
    FP=$(get_param "$PROXY_NODE_CLEAN_ARG" "fp" "chrome")
    PBK=$(get_param "$PROXY_NODE_CLEAN_ARG" "pbk" "")
    SID=$(get_param "$PROXY_NODE_CLEAN_ARG" "sid" "")
    ALPN=$(get_param "$PROXY_NODE_CLEAN_ARG" "alpn" "")
    INSECURE=$(get_param "$PROXY_NODE_CLEAN_ARG" "allowInsecure" "0")
    # WS / gRPC 参数
    WS_PATH=$(get_param "$PROXY_NODE_CLEAN_ARG" "path" "/")
    WS_HOST=$(get_param "$PROXY_NODE_CLEAN_ARG" "host" "$SNI")
    GRPC_SERVICE=$(get_param "$PROXY_NODE_CLEAN_ARG" "serviceName" "")

    # 用 Python 构造复杂 JSON（避免 bash 转义地狱）
    CONFIG_FILE="$CONFIG_FILE" \
    UUID="$UUID" HOST="$HOST" PORT="$PORT" \
    SECURITY="$SECURITY" SNI="$SNI" TYPE="$TYPE" FLOW="$FLOW" \
    FP="$FP" PBK="$PBK" SID="$SID" ALPN="$ALPN" \
    INSECURE="$INSECURE" WS_PATH="$WS_PATH" WS_HOST="$WS_HOST" \
    GRPC_SERVICE="$GRPC_SERVICE" \
    python3 - <<'PYEOF'
import json, os
def b(v): return v.lower() == "true" if v in ("true","false") else v
cfg = {
  "log": {"level": "info"},
  "inbounds": [
    {"type":"socks","tag":"socks-in","listen":"127.0.0.1","listen_port":1080},
    {"type":"mixed","tag":"mixed-in","listen":"127.0.0.1","listen_port":1081}
  ],
  "outbounds": []
}
ob = {
  "type":"vless","tag":"proxy",
  "server": os.environ["HOST"],
  "server_port": int(os.environ["PORT"]),
  "uuid": os.environ["UUID"]
}
flow = os.environ.get("FLOW","")
if flow: ob["flow"] = flow
security = os.environ["SECURITY"]
# --- TLS 配置 ---
if security in ("tls","reality"):
  tls = {"enabled": True, "server_name": os.environ["SNI"]}
  if os.environ.get("ALPN"):
    tls["alpn"] = os.environ["ALPN"].split(",")
  if os.environ.get("FP"):
    tls["utls"] = {"enabled": True, "fingerprint": os.environ["FP"]}
  if os.environ.get("INSECURE") == "1":
    tls["insecure"] = True
  if security == "reality":
    tls["reality"] = {
      "enabled": True,
      "public_key": os.environ["PBK"],
      "short_id": os.environ.get("SID","")
    }
  ob["tls"] = tls
# --- transport 配置 ---
ttype = os.environ["TYPE"]
if ttype == "ws":
  ob["transport"] = {
    "type":"ws",
    "path": os.environ["WS_PATH"],
    "headers": {"Host": os.environ["WS_HOST"]}
  }
elif ttype in ("grpc","gun"):
  ob["transport"] = {"type":"grpc","service_name": os.environ["GRPC_SERVICE"]}
# tcp / xtcp / quic：不加 transport 字段
cfg["outbounds"].append(ob)
with open(os.environ["CONFIG_FILE"],"w") as f:
  json.dump(cfg, f, indent=2)
print("vless config written")
PYEOF
    ;;

  # ============================================================
  # VMESS (vmess://base64(json))
  # ============================================================
  vmess)
    B64=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^vmess://||')
    # 解码 base64（自动补 padding）
    PADDING=$((4 - ${#B64} % 4))
    [ $PADDING -eq 4 ] && PADDING=0
    B64_PADDED="${B64}$(printf '=%.0s' $(seq 1 $PADDING))"
    JSON_STR=$(echo "$B64_PADDED" | base64 -d 2>/dev/null)
    if [ -z "$JSON_STR" ]; then
      echo "[ERROR] cannot decode vmess base64"
      exit 1
    fi
    echo "vmess json: $JSON_STR"
    CONFIG_FILE_ARG="$CONFIG_FILE" JSON_STR_ARG="$JSON_STR" python3 - <<'PYEOF'
import sys, json, os
v = json.loads(os.environ["JSON_STR_ARG"])
cfg = {
  "log": {"level": "info"},
  "inbounds": [
    {"type":"socks","tag":"socks-in","listen":"127.0.0.1","listen_port":1080},
    {"type":"mixed","tag":"mixed-in","listen":"127.0.0.1","listen_port":1081}
  ],
  "outbounds": []
}
ob = {
  "type":"vmess","tag":"proxy",
  "server": v["add"],
  "server_port": int(v["port"]),
  "uuid": v["id"]
}
if v.get("aid"):
  ob["alter_id"] = int(v["aid"])
if v.get("scy"):
  ob["security"] = v["scy"]
# TLS
if v.get("tls","") == "tls":
  tls = {"enabled": True}
  if v.get("sni"): tls["server_name"] = v["sni"]
  elif v.get("host"): tls["server_name"] = v["host"]
  if v.get("verify_cert", True) is False or v.get("allowInsecure"):
    tls["insecure"] = True
  ob["tls"] = tls
# transport
net = v.get("net","tcp")
if net == "ws":
  ob["transport"] = {
    "type":"ws",
    "path": v.get("path","/"),
    "headers": {"Host": v.get("host", v["add"])}
  }
elif net == "grpc":
  ob["transport"] = {"type":"grpc","service_name": v.get("path","")}
elif net == "h2":
  ob["transport"] = {
    "type":"http",
    "host": [v.get("host", v["add"])],
    "path": v.get("path","/")
  }
cfg["outbounds"].append(ob)
with open(os.environ["CONFIG_FILE_ARG"],"w") as f:
  json.dump(cfg, f, indent=2)
print("vmess config written")
PYEOF
    ;;

  # ============================================================
  # TROJAN (trojan://password@host:port?sni=xxx)
  # ============================================================
  trojan)
    PASS=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^trojan://([^@]+)@.*|\1|' | sed 's|%3A|:|g')
    HOST_PORT=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^trojan://[^@]+@([^/?]+).*|\1|')
    HOST=$(echo "$HOST_PORT" | cut -d: -f1)
    PORT=$(echo "$HOST_PORT" | cut -d: -f2)
    SNI=$(get_param "$PROXY_NODE_CLEAN_ARG" "sni" "$HOST")
    TYPE=$(get_param "$PROXY_NODE_CLEAN_ARG" "type" "tcp")
    INSECURE=$(get_param "$PROXY_NODE_CLEAN_ARG" "allowInsecure" "0")
    if [ "$INSECURE" = "1" ]; then INSECURE_BOOL=true; else INSECURE_BOOL=false; fi
    WS_PATH=$(get_param "$PROXY_NODE_CLEAN_ARG" "path" "/")
    WS_HOST=$(get_param "$PROXY_NODE_CLEAN_ARG" "host" "$SNI")
    GRPC_SERVICE=$(get_param "$PROXY_NODE_CLEAN_ARG" "serviceName" "")

    cat > "$CONFIG_FILE" <<EOF
{
  "log": {"level": "info"},
  "inbounds": [
    {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 1080},
    {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 1081}
  ],
  "outbounds": [
    {
      "type": "trojan",
      "tag": "proxy",
      "server": "$HOST",
      "server_port": $PORT,
      "password": "$PASS",
      "tls": {
        "enabled": true,
        "server_name": "$SNI",
        "insecure": $INSECURE_BOOL
      }$([ "$TYPE" = "ws" ] && echo ",
      \"transport\": {
        \"type\": \"ws\",
        \"path\": \"$WS_PATH\",
        \"headers\": {\"Host\": \"$WS_HOST\"}
      }")$([ "$TYPE" = "grpc" ] && echo ",
      \"transport\": {
        \"type\": \"grpc\",
        \"service_name\": \"$GRPC_SERVICE\"
      }")
    }
  ]
}
EOF
    ;;

  # ============================================================
  # SHADOWSOCKS (ss://method:password@host:port 或 ss://base64)
  # ============================================================
  ss)
    RAW=$(echo "$PROXY_NODE_CLEAN_ARG" | sed -E 's|^ss://||')
    # 处理 base64 形式 ss://base64(method:password@host:port)
    if [[ "$RAW" != *"@"* ]]; then
      # 尝试解码 base64（补齐 padding）
      PADDING=$((4 - ${#RAW} % 4))
      [ $PADDING -eq 4 ] && PADDING=0
      RAW_PADDED="${RAW}$(printf '=%.0s' $(seq 1 $PADDING))"
      DECODED=$(echo "$RAW_PADDED" | base64 -d 2>/dev/null)
      if [ -n "$DECODED" ] && [[ "$DECODED" == *"@"* ]]; then RAW="$DECODED"; fi
    fi
    if [[ "$RAW" == *"@"* ]]; then
      METHOD_PASS=$(echo "$RAW" | sed -E 's|^(.*)@.*|\1|')
      HOST_PORT=$(echo "$RAW" | sed -E 's|^.*@([^?]+).*|\1|')
      METHOD=$(echo "$METHOD_PASS" | cut -d: -f1)
      PASS=$(echo "$METHOD_PASS" | cut -d: -f2-)
    else
      echo "[ERROR] cannot parse ss:// link"
      exit 1
    fi
    HOST=$(echo "$HOST_PORT" | cut -d: -f1)
    PORT=$(echo "$HOST_PORT" | cut -d: -f2)

    cat > "$CONFIG_FILE" <<EOF
{
  "log": {"level": "info"},
  "inbounds": [
    {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 1080},
    {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 1081}
  ],
  "outbounds": [
    {
      "type": "shadowsocks",
      "tag": "proxy",
      "server": "$HOST",
      "server_port": $PORT,
      "method": "$METHOD",
      "password": "$PASS"
    }
  ]
}
EOF
    ;;

  # ============================================================
  # TUIC v5 (tuic://uuid:password@host:port?params)
  # ============================================================
  tuic)
    # 使用 Python 解析 TUIC URL（更可靠）
    CONFIG_FILE="$CONFIG_FILE" PROXY_NODE_CLEAN_ARG="$PROXY_NODE_CLEAN_ARG" python3 - <<'PYEOF'
import re, os, json

node = os.environ["PROXY_NODE_CLEAN_ARG"]
# 去掉 #fragment
node = re.sub(r'#.*$', '', node)
# 匹配 tuic://uuid:password@host:port?key=value
m = re.match(r'^tuic://([^:@]+):([^@]+)@([^?/]+)(?:\?([^#]*))?', node)
if not m:
    print(f"[ERROR] cannot parse tuic URL: {node}")
    exit(1)

uuid = m.group(1)
password = m.group(2)
host_port = m.group(3)
query = m.group(4) or ""

parts = host_port.split(":")
host = parts[0]
port = int(parts[1]) if len(parts) > 1 else 443

# 解析 query 参数
params = {}
for pair in query.split("&"):
    if "=" in pair:
        k, v = pair.split("=", 1)
        params[k] = v
    else:
        params[pair] = "true"

sni = params.get("sni", str(host))
congestion = params.get("congestion_control", "cubic")
udp_mode = params.get("udp_relay_mode", "native")
# 兼容 insecure / allow_insecure / allowInsecure
insecure_val = params.get("allow_insecure", params.get("insecure", params.get("allowInsecure", "0")))
insecure = insecure_val == "1"
zero_rtt = params.get("zero_rtt", "0") == "1"
heartbeat = params.get("heartbeat", "30s")

tls = {"enabled": True, "server_name": sni}
if insecure:
    tls["insecure"] = True
ch = params.get("cert_hash", "")
cp = params.get("cert_pubkey", "")
if ch:
    tls["pin_certificate"] = True
    tls["certificate_hash"] = ch
elif cp:
    tls["pin_certificate"] = True
    tls["certificate_public_key"] = cp

cfg = {
    "log": {"level": "info"},
    "inbounds": [
        {"type": "socks", "tag": "socks-in", "listen": "127.0.0.1", "listen_port": 1080},
        {"type": "mixed", "tag": "mixed-in", "listen": "127.0.0.1", "listen_port": 1081}
    ],
    "outbounds": [{
        "type": "tuic",
        "tag": "proxy",
        "server": host,
        "server_port": port,
        "uuid": uuid,
        "password": password,
        "congestion_control": congestion,
        "udp_relay_mode": udp_mode,
        "zero_rtt_handshake": zero_rtt,
        "heartbeat": heartbeat,
        "tls": tls
    }]
}

with open(os.environ["CONFIG_FILE"], "w") as f:
    json.dump(cfg, f, indent=2)
print(f"tuic config: {host}:{port} uuid={uuid[:8]}...")
PYEOF
    ;;

  *)
    echo "Unsupported protocol: $PROTO"
    echo "Supported: hysteria2/hy2, vless, vmess, trojan, ss, tuic"
    exit 1
    ;;
esac

echo "server: ${HOST:-N/A}:${PORT:-N/A}"
echo "config generated:"
cat "$CONFIG_FILE" | jq .

echo "=== 3. 启动 sing-box（后台） ==="
LOG_FILE="/tmp/singbox.log"
setsid nohup "$SINGBOX_BIN" run -c "$CONFIG_FILE" > "$LOG_FILE" 2>&1 < /dev/null &
SINGBOX_PID=$!
disown $SINGBOX_PID 2>/dev/null || true
echo "sing-box started (PID=$SINGBOX_PID)"

# 等待启动并验证存活
sleep 3
if kill -0 $SINGBOX_PID 2>/dev/null; then
  echo "sing-box alive after 3s"
else
  echo "sing-box failed to start after 3s"
  echo "=== singbox.log ==="
  cat "$LOG_FILE"
  exit 1
fi

# 再等几秒确认进程稳定
sleep 5
if kill -0 $SINGBOX_PID 2>/dev/null; then
  echo "sing-box alive after 8s"
else
  echo "sing-box died after 8s"
  echo "=== singbox.log ==="
  cat "$LOG_FILE"
  exit 1
fi

echo "=== 4. 验证代理出网 ==="
PROXY_OK=false
for i in 1 2 3 4 5; do
  if curl -s --socks5 127.0.0.1:1080 --max-time 10 "https://api.ipify.org?format=json" > /tmp/ipinfo.json 2>&1; then
    if jq -e .ip /tmp/ipinfo.json > /dev/null 2>&1; then
      echo "proxy working, ip:"
      cat /tmp/ipinfo.json | jq .
      PROXY_OK=true
      break
    fi
  fi
  echo "waiting for sing-box... ($i/5)"
  sleep 2
  if ! kill -0 $SINGBOX_PID 2>/dev/null; then
    echo "sing-box died during verification!"
    cat "$LOG_FILE"
    exit 1
  fi
done

if [ "$PROXY_OK" = "false" ]; then
  if curl -s --socks5 127.0.0.1:1080 --max-time 15 "https://ipinfo.io/json" > /tmp/ipinfo.json 2>&1; then
    if jq -e .ip /tmp/ipinfo.json > /dev/null 2>&1; then
      echo "proxy working (via ipinfo.io), ip:"
      cat /tmp/ipinfo.json | jq .
      PROXY_OK=true
    fi
  fi
fi

if [ "$PROXY_OK" = "false" ]; then
  echo "proxy verification failed"
  echo "=== singbox.log ==="
  cat "$LOG_FILE"
  exit 1
fi

echo "$SINGBOX_PID" > /tmp/singbox.pid
echo "sing-box PID saved to /tmp/singbox.pid"
