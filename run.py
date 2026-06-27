#!/usr/bin/env python3
"""
Privacy Compliance Agent — 全流程 pipeline。

将四个阶段串联为完整的隐私合规分析流程:
1. 文本分句 (segment)
2. 句子分类 (classify)
3. 同意权抽取 (extract)
4. 动态验证 (verify) — Frida + mitmproxy
5. 报告生成 (report)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def cmd_segment(args):
    from tools.segment_policy import segment_policy, write_json, write_csv

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_path.glob("*.txt")) if input_path.is_dir() else [input_path]
    print(f"分句: {len(files)} 个文件, 策略={args.strategy}\n")

    for f in files:
        text = f.read_text(encoding="utf-8")
        records = segment_policy(text, f.name, strategy=args.strategy)
        out = output_dir / f"{f.stem}_sentences.json"
        write_json(records, str(out))
        print(f"  {f.name} -> {len(records)} 条句子")

    print(f"\n输出目录: {output_dir}")


def cmd_classify(args):
    from tools.classify_sentences import load_sentences, classify

    input_dir = Path(args.input)
    jsons = sorted(input_dir.glob("*_sentences.json"))
    if not jsons:
        print(f"未找到分句文件: {input_dir}")
        return

    records = load_sentences([str(j) for j in jsons])
    print(f"加载 {len(records)} 条句子")

    results = classify(records, n_clusters=args.n_clusters, use_tfidf=args.use_tfidf)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    related = sum(1 for r in results if r["is_personal_info_related"] == "是")
    print(f"分类完成: 相关 {related} / 总计 {len(results)}")
    print(f"输出: {out}")


def cmd_extract(args):
    from agents.consent_extractor import main as extractor_main
    sys.argv = ['consent_extractor', args.input, '--output', args.output,
                '--api-key', args.api_key, '--model', args.model]
    if args.base_url:
        sys.argv.extend(['--base-url', args.base_url])
    extractor_main()


def cmd_verify(args):
    if args.mode == "frida":
        from agents.frida_tester import PrivacyTester
        tester = PrivacyTester(results_dir=args.output)
        if args.app:
            from agents.frida_tester import APP_PACKAGES
            if args.app in APP_PACKAGES and tester.connect_device():
                tester.test_app(args.app, APP_PACKAGES[args.app])
        else:
            tester.run_all()
    elif args.mode == "mitm":
        from agents.mitm_monitor import main as mitm_main
        mitm_main()


def cmd_report(args):
    from tools.analyze_results import analyze_frida_results, analyze_mitm_results, generate_report
    frida = analyze_frida_results(Path(args.frida_dir))
    mitm = analyze_mitm_results(Path(args.mitm_dir))
    generate_report(frida, mitm, Path(args.output))


def main():
    parser = argparse.ArgumentParser(
        description="Privacy Compliance Agent - 移动应用隐私合规分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 1. 对隐私政策文本分句
  python run.py segment --input data/sample_policies --output results/sentences

  # 2. 分类句子 (判断是否涉及个人信息)
  python run.py classify --input results/sentences --output results/classified.json

  # 3. 提取同意权信息
  python run.py extract --input data/sample_policies --api-key sk-xxx

  # 4. Frida 动态验证
  python run.py verify --mode frida --app QQ音乐

  # 5. 生成报告
  python run.py report
        """
    )
    sub = parser.add_subparsers(dest="command")

    p_seg = sub.add_parser("segment", help="隐私政策文本分句")
    p_seg.add_argument("--input", required=True, help=".txt 文件或目录")
    p_seg.add_argument("--output", default="results/sentences")
    p_seg.add_argument("--strategy", choices=["conservative", "aggressive"], default="conservative")

    p_cls = sub.add_parser("classify", help="句子分类 (个人信息相关性)")
    p_cls.add_argument("--input", required=True, help="分句 JSON 所在目录")
    p_cls.add_argument("--output", default="results/classified.json")
    p_cls.add_argument("--n-clusters", type=int, default=10)
    p_cls.add_argument("--use-tfidf", action="store_true")

    p_ext = sub.add_parser("extract", help="同意权/撤销同意权抽取")
    p_ext.add_argument("--input", required=True, help=".txt 文件或目录")
    p_ext.add_argument("--output", default="results/consent_extraction")
    p_ext.add_argument("--api-key", required=True)
    p_ext.add_argument("--base-url", default="")
    p_ext.add_argument("--model", default="gpt-4o")

    p_ver = sub.add_parser("verify", help="动态验证 (Frida/mitmproxy)")
    p_ver.add_argument("--mode", choices=["frida", "mitm"], required=True)
    p_ver.add_argument("--app", help="指定 APP (仅 frida 模式)")
    p_ver.add_argument("--output", default="results/frida_tests")

    p_rpt = sub.add_parser("report", help="生成合规评估报告")
    p_rpt.add_argument("--frida-dir", default="results/frida_tests")
    p_rpt.add_argument("--mitm-dir", default="results/mitm_captures")
    p_rpt.add_argument("--output", default="results/compliance_report.md")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    {"segment": cmd_segment, "classify": cmd_classify, "extract": cmd_extract,
     "verify": cmd_verify, "report": cmd_report}[args.command](args)


if __name__ == "__main__":
    main()
