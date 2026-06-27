#!/usr/bin/env python3
"""
Agent: 使用 Frida Hook 自动化检测 APP 实际收集的个人信息。

对比隐私政策声明 vs 应用实际行为，验证隐私权力的真实性。
监控 5 类隐私数据: 设备号、MAC地址、地理位置、已安装应用列表、剪贴板。
"""

import frida
import subprocess
import time
import json
import os
import sys
import csv
from datetime import datetime
from pathlib import Path


APP_PACKAGES = {
    "BOSS直聘": "com.hpbr.bosszhipin",
    "大众点评": "com.dianping.v1",
    "方特旅游": "cn.fantawild.travels",
    "今日头条": "com.ss.android.article.news",
    "MOMO": "com.immomo.momo",
    "七猫免费小说": "com.kmxs.reader",
    "QQ音乐": "com.tencent.qqmusic",
    "搜狐视频": "com.sohu.sohuvideo",
    "搜狐新闻": "com.sohu.newsclient",
    "Soul": "cn.soulapp.android",
    "携程旅行": "ctrip.android.view",
    "新浪新闻": "com.sina.news",
    "央视新闻": "cn.cntvnews",
    "中国移动": "com.greenpoint.android.mc10086.activity",
    "作业帮": "com.baidu.homework",
    "58同城": "com.wuba",
    "Keep": "com.gotokeep.keep",
    "懂车帝": "com.ss.android.auto",
    "去哪儿旅行": "com.Qunar",
    "全民K歌": "com.tencent.karaoke",
    "小红书": "com.xingin.xhs",
}


class PrivacyTester:
    def __init__(self, results_dir: str = "results/frida_tests"):
        self.device = None
        self.session = None
        self.script = None
        self.collected_data = {}
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def connect_device(self) -> bool:
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if 'device' not in result.stdout:
                print("未检测到 Android 设备")
                return False
            self.device = frida.get_usb_device(timeout=10)
            print(f"已连接: {self.device}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def _get_pid(self, package: str) -> int | None:
        try:
            result = subprocess.run(['adb', 'shell', f'pidof {package}'],
                                    capture_output=True, text=True)
            if result.stdout.strip():
                return int(result.stdout.strip().split()[0])
        except Exception:
            pass
        return None

    def _start_app(self, package: str) -> bool:
        try:
            subprocess.run(['adb', 'shell', 'am', 'force-stop', package], capture_output=True)
            time.sleep(1)
            subprocess.run(['adb', 'shell', 'monkey', '-p', package, '-c',
                           'android.intent.category.LAUNCHER', '1'],
                          capture_output=True, text=True, timeout=10)
            time.sleep(8)
            return True
        except Exception as e:
            print(f"  启动失败: {e}")
            return False

    def _stop_app(self, package: str):
        subprocess.run(['adb', 'shell', 'am', 'force-stop', package], capture_output=True)
        time.sleep(1)

    def _on_message(self, message, data):
        if message['type'] == 'send':
            payload = message['payload']
            msg_type = payload.get('type', '')
            if msg_type == 'info':
                print(f"    [info] {payload['message']}")
            elif msg_type in ['device_id', 'mac_address', 'location', 'installed_apps', 'clipboard']:
                self.collected_data.setdefault(msg_type, []).append(payload)
                print(f"    [hook] {msg_type}: {payload.get('subtype', '')} = {str(payload.get('value', ''))[:60]}")

    def _attach_hook(self, package: str) -> bool:
        hook_path = Path(__file__).parent.parent / "hooks" / "frida" / "privacy_hook.js"
        if not hook_path.exists():
            print(f"  Hook 脚本不存在: {hook_path}")
            return False

        for attempt in range(5):
            pid = self._get_pid(package)
            if pid:
                break
            time.sleep(2)

        if not pid:
            print("  找不到进程")
            return False

        try:
            self.session = self.device.attach(pid)
            self.script = self.session.create_script(hook_path.read_text(encoding='utf-8'))
            self.script.on('message', self._on_message)
            self.script.load()
            print(f"  Hook 已注入 (PID: {pid})")
            return True
        except Exception as e:
            print(f"  注入失败: {e}")
            return False

    def _simulate_actions(self, duration: int = 30):
        print(f"  模拟用户操作 ({duration}s)...")
        cmds = [
            ['adb', 'shell', 'input', 'tap', '500', '1000'],
            ['adb', 'shell', 'input', 'swipe', '500', '1500', '500', '500', '300'],
            ['adb', 'shell', 'input', 'tap', '300', '800'],
            ['adb', 'shell', 'input', 'tap', '700', '1200'],
        ]
        start = time.time()
        while time.time() - start < duration:
            for cmd in cmds:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=2)
                    time.sleep(2)
                except Exception:
                    pass
                if time.time() - start >= duration:
                    break

    def test_app(self, app_name: str, package: str) -> dict | None:
        print(f"\n{'='*50}")
        print(f"测试: {app_name} ({package})")
        print(f"{'='*50}")

        self.collected_data = {}

        if not self._start_app(package):
            return None
        if not self._attach_hook(package):
            self._stop_app(package)
            return None

        try:
            self._simulate_actions(30)
        except KeyboardInterrupt:
            print("\n  中断")

        self._stop_app(package)
        try:
            if self.script:
                self.script.unload()
            if self.session:
                self.session.detach()
        except Exception:
            pass

        result = {
            'app_name': app_name,
            'package_name': package,
            'test_time': datetime.now().isoformat(),
            'collected_data': self.collected_data,
            'summary': {k: len(v) for k, v in self.collected_data.items()}
        }

        out = self.results_dir / f"{app_name}_result.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"\n  结果: {result['summary']}")
        print(f"  保存: {out}")
        return result

    def run_all(self):
        if not self.connect_device():
            return

        results = []
        for name, pkg in APP_PACKAGES.items():
            r = self.test_app(name, pkg)
            if r:
                results.append(r)
            time.sleep(3)

        self._save_summary(results)

    def _save_summary(self, results: list[dict]):
        csv_path = self.results_dir / f"summary_{datetime.now():%Y%m%d_%H%M%S}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['APP', '包名', '设备号', 'MAC地址', '位置', '应用列表', '剪贴板'])
            for r in results:
                s = r['summary']
                w.writerow([r['app_name'], r['package_name'],
                           s.get('device_id', 0), s.get('mac_address', 0),
                           s.get('location', 0), s.get('installed_apps', 0),
                           s.get('clipboard', 0)])
        print(f"\n汇总: {csv_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Frida 隐私检测 Agent")
    parser.add_argument("--app", help="指定 APP 名称（不指定则测试全部）")
    parser.add_argument("--output", default="results/frida_tests")
    args = parser.parse_args()

    tester = PrivacyTester(results_dir=args.output)

    if args.app:
        if args.app not in APP_PACKAGES:
            print(f"未知 APP: {args.app}")
            print(f"可用: {', '.join(APP_PACKAGES.keys())}")
            return
        if tester.connect_device():
            tester.test_app(args.app, APP_PACKAGES[args.app])
    else:
        tester.run_all()


if __name__ == '__main__':
    main()
