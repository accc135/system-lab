# Privacy Compliance Agent

移动应用隐私合规性自动化分析系统，覆盖从隐私政策文本分析到 Android 应用动态验证的完整流程。

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    run.py（agnet项目运行） (pipeline)                 │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│ segment  │ classify │ extract  │ verify   │ report   │
│ 文本分句  │ 句子分类   │ 权利抽取 │ 静态动态验证  │ 报告生成 │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     │          │          │          │          │
  tools/     tools/     agents/   agents/    tools/
  segment    classify   consent   frida      analyze
  _policy    _sentences _extractor _tester   _results
                                  agents/
                                  mitm_monitor
```

## 快速开始

```bash
pip install -r requirements.txt

# 1. 文本分句 — 将隐私政策切分为结构化句子
python run.py segment --input data/sample_policies --output results/sentences

# 2. 句子分类 — 判断哪些句子涉及个人信息处理
python run.py classify --input results/sentences --output results/classified.json --use-tfidf

# 3. 同意权抽取 — 用 LLM 提取同意权/撤销同意权的结构化信息
python run.py extract --input data/sample_policies --api-key $OPENAI_API_KEY

# 4. 动态验证 — Frida Hook 检测 APP 实际收集的个人信息
bash scripts/setup_frida.sh            # 部署 Frida Server
python run.py verify --mode frida      # 运行全部 APP 测试
python run.py verify --mode frida --app QQ音乐  # 测试单个 APP

# 5. 网络流量分析 — mitmproxy 拦截隐私数据上传
python run.py verify --mode mitm

# 6. 生成报告
python run.py report
```

## 项目结构

```
├── run.py                    # 统一入口 (pipeline)
├── agents/
│   ├── consent_extractor.py  # LLM 同意权抽取 agent
│   ├── frida_tester.py       # Frida 动态检测 agent
│   └── mitm_monitor.py       # 网络流量监控 agent
├── tools/
│   ├── segment_policy.py     # 隐私政策文本分句
│   ├── classify_sentences.py # 基于聚类的句子分类
│   └── analyze_results.py    # 结果分析与报告生成
├── hooks/
│   ├── frida/
│   │   ├── privacy_hook.js        # Frida hook: 5 类隐私 API 监控
│   │   └── privacy_hook_bypass.js # Frida hook + SSL Pinning 绕过
│   └── mitm_interceptor.py        # mitmproxy addon
├── scripts/
│   └── setup_frida.sh        # Frida Server 自动部署
├── data/
│   └── sample_policies/      # 示例隐私政策文本
├── results/                  # 输出目录 (gitignored)
├── config.example.yaml       # 配置模板
└── requirements.txt
```

## 模块说明

### Agents

| Agent | 功能 | 依赖 |
|-------|------|------|
| `consent_extractor` | 从隐私政策中提取同意权行使方式 (UI路径/系统设置/联系客服) | OpenAI API |
| `frida_tester` | Hook Android API 监控 APP 实际收集的隐私数据 | Frida, ADB |
| `mitm_monitor` | 拦截网络流量分析隐私数据上传 | mitmproxy |

### Tools

| Tool | 功能 | 方法 |
|------|------|------|
| `segment_policy` | 中文隐私政策分句，保留段落/行号信息 | 规则 (条目标记 + 标点) |
| `classify_sentences` | 判断句子是否与个人信息利用相关 | KMeans 聚类 + 关键词标签 |
| `analyze_results` | 汇总 Frida/mitmproxy 结果生成评估报告 | 统计分析 |

### Hooks

| Hook | 监控目标 |
|------|---------|
| `privacy_hook.js` | IMEI/Android ID/OAID, MAC地址, GPS位置, 已安装应用列表, 剪贴板 |
| `privacy_hook_bypass.js` | 同上 + SSL Pinning 绕过 (OkHttp3/TrustManager/WebView) |
| `mitm_interceptor.py` | 正则匹配请求/响应中的 IMEI、坐标、MAC、应用列表 |

## 分析流程

```
隐私政策文本 (.txt)
       │
       ├─ [segment] 分句 ──► 结构化句子 (JSON)
       │                         │
       │                    [classify] 分类 ──► 个人信息相关句子
       │
       └─ [extract] LLM 抽取 ──► 同意权结构 (JSON)
                                      │
                                      ▼
                              同意权声明 vs 实际行为
                                      ▲
                                      │
       Android APP ─── [verify] ──────┘
       │                    │
       ├─ Frida Hook       ├─ 设备号/位置/MAC/应用列表/剪贴板
       └─ mitmproxy        └─ 网络流量中的隐私数据
                                      │
                                 [report] ──► 合规评估报告 (.md)
```

## 环境要求

- Python 3.10+
- Android 设备 (动态分析需要 root 或模拟器)
- ADB 工具
- OpenAI 兼容 API (同意权抽取)
