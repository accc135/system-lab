"""
mitmproxy addon: 拦截并分析 APP 网络流量中的隐私数据。

用法: mitmweb -s hooks/mitm_interceptor.py
"""

from mitmproxy import http, ctx
import json
import re
from datetime import datetime
from pathlib import Path


class PrivacyInterceptor:
    def __init__(self):
        self.results_dir = Path("results/mitm_captures")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.captured = {
            'device_ids': [], 'locations': [], 'mac_addresses': [],
            'app_lists': [], 'all_requests': []
        }

        self.patterns = {
            'imei': r'\b\d{15}\b',
            'android_id': r'\b[a-f0-9]{16}\b',
            'mac': r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b',
            'latitude': r'lat(?:itude)?["\s:=]+(-?\d+\.\d+)',
            'longitude': r'lon(?:gitude)?["\s:=]+(-?\d+\.\d+)',
        }

    def request(self, flow: http.HTTPFlow):
        info = {
            'timestamp': datetime.now().isoformat(),
            'method': flow.request.method,
            'url': flow.request.url,
            'host': flow.request.host,
        }

        if flow.request.content:
            try:
                body = flow.request.content.decode('utf-8', errors='ignore')
                self._analyze(body, info['url'])
            except Exception:
                pass

        self.captured['all_requests'].append(info)

    def response(self, flow: http.HTTPFlow):
        if flow.response and flow.response.content:
            try:
                body = flow.response.content.decode('utf-8', errors='ignore')
                self._analyze(body, flow.request.url, is_response=True)
            except Exception:
                pass

    def _analyze(self, text: str, url: str, is_response: bool = False):
        lower = text.lower()
        src = 'response' if is_response else 'request'

        if 'imei' in lower or 'device' in lower:
            for m in re.findall(self.patterns['imei'], text):
                self.captured['device_ids'].append(
                    {'type': 'IMEI', 'value': m, 'url': url, 'source': src})
                ctx.log.warn(f"[privacy] IMEI: {m} -> {url[:80]}")

        if 'mac' in lower or 'wifi' in lower:
            for m in re.findall(self.patterns['mac'], text):
                mac = ''.join(m) if isinstance(m, tuple) else m
                self.captured['mac_addresses'].append(
                    {'value': mac, 'url': url, 'source': src})
                ctx.log.warn(f"[privacy] MAC: {mac} -> {url[:80]}")

        if 'lat' in lower or 'lon' in lower or 'location' in lower:
            lats = re.findall(self.patterns['latitude'], lower)
            lons = re.findall(self.patterns['longitude'], lower)
            if lats and lons:
                self.captured['locations'].append(
                    {'lat': lats[0], 'lon': lons[0], 'url': url, 'source': src})
                ctx.log.warn(f"[privacy] Location: {lats[0]},{lons[0]} -> {url[:80]}")

        if 'package' in lower or 'app' in lower:
            pkgs = re.findall(r'com\.[a-z0-9_]+\.[a-z0-9_.]+', lower)
            if len(pkgs) > 3:
                self.captured['app_lists'].append(
                    {'count': len(pkgs), 'sample': pkgs[:5], 'url': url, 'source': src})
                ctx.log.warn(f"[privacy] App list ({len(pkgs)}) -> {url[:80]}")

    def done(self):
        out = self.results_dir / f"capture_{datetime.now():%Y%m%d_%H%M%S}.json"
        summary = {k: len(v) for k, v in self.captured.items()}
        data = {'summary': summary, 'captured': self.captured}
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        ctx.log.info(f"[privacy] 结果已保存: {out} | {summary}")


addons = [PrivacyInterceptor()]
