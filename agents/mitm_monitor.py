#!/usr/bin/env python3
"""
Agent: 使用 mitmproxy 拦截网络流量，检测 APP 上传的隐私数据。

与 Frida Hook Agent 互补：Frida 在客户端层面监控 API 调用，
mitmproxy 在网络层面验证隐私数据是否真的被发送到服务器。
"""

import subprocess
import sys
from pathlib import Path


def get_local_ip() -> str | None:
    try:
        result = subprocess.run(['ifconfig'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'inet ' in line and '127.0.0.1' not in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'inet' and i + 1 < len(parts):
                        ip = parts[i + 1]
                        if ip.startswith('192.168') or ip.startswith('10.'):
                            return ip
    except Exception:
        pass
    return None


def main():
    addon = Path(__file__).parent.parent / "hooks" / "mitm_interceptor.py"
    if not addon.exists():
        print(f"错误: {addon} 不存在")
        return

    ip = get_local_ip()
    print("=" * 50)
    print("mitmproxy 隐私流量监控")
    print("=" * 50)
    if ip:
        print(f"\n手机代理: {ip}:8080")
        print(f"证书安装: http://mitm.it\n")

    mode = sys.argv[1] if len(sys.argv) > 1 else "web"

    if mode == "web":
        print("启动 mitmweb (浏览器: http://localhost:8081)")
        subprocess.run(['mitmweb', '--web-port', '8081', '-s', str(addon),
                       '--set', 'block_global=false'])
    elif mode == "cli":
        print("启动 mitmproxy (终端模式)")
        subprocess.run(['mitmproxy', '-s', str(addon), '--set', 'block_global=false'])
    else:
        print("启动 mitmdump (日志模式)")
        subprocess.run(['mitmdump', '-s', str(addon), '--set', 'block_global=false'])


if __name__ == '__main__':
    main()
