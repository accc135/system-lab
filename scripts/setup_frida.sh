#!/bin/bash
set -e

echo "=============================="
echo "Frida Server 部署"
echo "=============================="

FRIDA_VERSION=$(frida --version)
echo "Frida 版本: $FRIDA_VERSION"

ARCH=$(adb shell getprop ro.product.cpu.abi | tr -d '\r')
echo "设备架构: $ARCH"

SERVER_NAME="frida-server-${FRIDA_VERSION}-android-${ARCH}"
SERVER_URL="https://github.com/frida/frida/releases/download/${FRIDA_VERSION}/${SERVER_NAME}.xz"

if [ -f "frida-server" ]; then
    echo "frida-server 已存在"
else
    echo "下载 $SERVER_URL ..."
    curl -L -o "${SERVER_NAME}.xz" "$SERVER_URL"
    xz -d "${SERVER_NAME}.xz"
    mv "$SERVER_NAME" frida-server
    chmod +x frida-server
fi

echo "部署到设备..."
adb push frida-server /data/local/tmp/
adb shell "chmod 755 /data/local/tmp/frida-server"

echo "启动 frida-server..."
adb shell "pkill -9 frida-server" 2>/dev/null || true
adb shell "/data/local/tmp/frida-server &" &
sleep 2

if adb shell "ps -A | grep frida-server" > /dev/null; then
    echo "frida-server 已启动"
else
    echo "启动失败"
    exit 1
fi

echo ""
echo "可以运行: python agents/frida_tester.py"
