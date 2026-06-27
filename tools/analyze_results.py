#!/usr/bin/env python3
"""
Agent: 分析 Frida 和 mitmproxy 的测试结果，生成合规评估报告。
"""

import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict


def analyze_frida_results(results_dir: Path) -> dict:
    files = list(results_dir.glob("*_result.json"))
    if not files:
        return {}

    stats = defaultdict(lambda: defaultdict(int))
    apps = []

    for f in files:
        data = json.loads(f.read_text(encoding='utf-8'))
        name = data.get('app_name', f.stem)
        summary = data.get('summary', {})
        apps.append({'app': name, **summary})

        for key, count in summary.items():
            if count > 0:
                stats[key]['detected_apps'] += 1
                stats[key]['total_count'] += count

    return {'apps': apps, 'stats': dict(stats), 'total': len(files)}


def analyze_mitm_results(results_dir: Path) -> dict:
    files = sorted(results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        return {}

    latest = json.loads(files[0].read_text(encoding='utf-8'))
    return {
        'file': files[0].name,
        'summary': latest.get('summary', {}),
        'device_ids': latest.get('captured', {}).get('device_ids', [])[:10],
        'locations': latest.get('captured', {}).get('locations', [])[:10],
    }


def generate_report(frida_data: dict, mitm_data: dict, output: Path):
    lines = ["# 隐私合规评估报告\n"]

    if frida_data:
        lines.append(f"## Frida Hook 检测结果 ({frida_data['total']} 个 APP)\n")
        lines.append("| APP | 设备号 | MAC | 位置 | 应用列表 | 剪贴板 |")
        lines.append("|-----|--------|-----|------|---------|--------|")
        for app in sorted(frida_data['apps'], key=lambda x: sum(
                x.get(k, 0) for k in ['device_id', 'mac_address', 'location']), reverse=True):
            lines.append(f"| {app['app']} | {app.get('device_id', 0)} | "
                        f"{app.get('mac_address', 0)} | {app.get('location', 0)} | "
                        f"{app.get('installed_apps', 0)} | {app.get('clipboard', 0)} |")

        lines.append("\n### 统计概览\n")
        for key, stat in frida_data['stats'].items():
            lines.append(f"- **{key}**: {stat['detected_apps']} 个 APP 涉及, "
                        f"共 {stat['total_count']} 次访问")

    if mitm_data:
        lines.append(f"\n## 网络流量分析\n")
        lines.append(f"数据文件: {mitm_data.get('file', 'N/A')}\n")
        s = mitm_data.get('summary', {})
        lines.append(f"- 总请求: {s.get('all_requests', 0)}")
        lines.append(f"- 设备号泄露: {s.get('device_ids', 0)}")
        lines.append(f"- 位置泄露: {s.get('locations', 0)}")
        lines.append(f"- MAC 泄露: {s.get('mac_addresses', 0)}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    print(f"报告: {output}")


def main():
    parser = argparse.ArgumentParser(description="隐私测试结果分析")
    parser.add_argument("--frida-dir", default="results/frida_tests", help="Frida 结果目录")
    parser.add_argument("--mitm-dir", default="results/mitm_captures", help="MITM 结果目录")
    parser.add_argument("--output", default="results/compliance_report.md")
    args = parser.parse_args()

    frida_data = analyze_frida_results(Path(args.frida_dir))
    mitm_data = analyze_mitm_results(Path(args.mitm_dir))

    if not frida_data and not mitm_data:
        print("未找到任何测试结果")
        print("请先运行:")
        print("  python agents/frida_tester.py")
        print("  python agents/mitm_monitor.py")
        return

    generate_report(frida_data, mitm_data, Path(args.output))


if __name__ == '__main__':
    main()
