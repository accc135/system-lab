#!/usr/bin/env python3
"""
Agent: 从隐私政策文本中提取同意权/撤销同意权的结构化信息。

输入: 隐私政策 .txt 文件（单个或目录）
输出: 结构化 JSON 报告
"""

import json
import os
import argparse
from pathlib import Path
from openai import OpenAI


SYSTEM_PROMPT = """
你是一个专业的"隐私合规分析师"与"移动端自动化测试工程师"。你的任务是阅读APP的隐私政策文本，提取用户行使"同意权/撤销同意权"的具体执行方式和UI开关位置。

# 分析维度
你需要从文本中提取以下三个维度的同意权信息：
1. 应用级业务撤回 (personalized_ads)：例如关闭个性化推荐、定向广告、营销推送等。
2. 系统级权限撤回 (system_permissions)：例如撤回相机、定位、麦克风等系统硬件权限。
3. 彻底撤回同意 (account_cancellation)：例如注销账号、清除所有数据。

# 抽取规则与字段定义
1. `has_in_app_switch` (Boolean): 政策中是否明确写明了APP内部有具体的开关、按钮或明确的页面路径？如果是则为 true；如果仅要求发邮件、打电话、找客服或去手机操作系统设置中修改，则为 false。
2. `method` (String): 严格从以下枚举值中选择其一：
   - "ui_navigation" (App内部有明确路径)
   - "system_settings" (需要去iOS/Android手机操作系统的设置里改)
   - "external_contact" (需要发邮件、打电话或联系人工客服)
   - "not_mentioned" (文本中未提及或描述模糊)
3. `target_path` (List[String]): 仅当 method 为 "ui_navigation" 时提取。将文本描述的路径拆分为数组，例如 ["我的", "设置", "隐私保护"]。如无则为 []。
4. `contact_info` (Object): 仅当 method 为 "external_contact" 时提取。包含 "email" 或 "phone" 字段。如无则为空对象 {}。

# 输出约束
你必须以纯 JSON 格式输出结果，严格遵循以下结构。

{
  "app_name": "从文本中推断出的APP名称",
  "consent_rights": {
    "personalized_ads": {
      "has_in_app_switch": true/false,
      "method": "枚举值",
      "target_path": [],
      "contact_info": {}
    },
    "system_permissions": { ... },
    "account_cancellation": { ... }
  }
}
"""


def analyze_policy(client: OpenAI, policy_text: str, model: str = "gpt-4o") -> dict | None:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"以下是需要分析的隐私政策文本：\n\n{policy_text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content.strip())
    except json.JSONDecodeError as e:
        print(f"  JSON 解析失败: {e}")
        return None
    except Exception as e:
        print(f"  API 请求出错: {e}")
        return None


def process_file(client: OpenAI, input_path: Path, output_dir: Path, model: str):
    print(f"处理: {input_path.name}")

    text = input_path.read_text(encoding="utf-8")
    if not text.strip():
        print(f"  跳过空文件")
        return

    result = analyze_policy(client, text, model)
    if not result:
        print(f"  分析失败")
        return

    app_name = result.get("app_name", "")
    if not app_name or app_name in ["未知", "unknown"]:
        app_name = input_path.stem

    out = output_dir / f"{app_name}_report.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {out}")


def main():
    parser = argparse.ArgumentParser(description="隐私政策同意权抽取 Agent")
    parser.add_argument("input", help=".txt 文件或包含 .txt 的目录")
    parser.add_argument("--output", default="results/consent_extraction", help="输出目录")
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", ""), help="OpenAI API Key")
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--model", default="gpt-4o")
    args = parser.parse_args()

    if not args.api_key:
        print("错误: 请通过 --api-key 或 OPENAI_API_KEY 环境变量提供 API Key")
        return

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    if input_path.is_dir():
        files = sorted(input_path.glob("*.txt"))
        print(f"找到 {len(files)} 个文件\n")
        for f in files:
            process_file(client, f, output_dir, args.model)
    elif input_path.is_file():
        process_file(client, input_path, output_dir, args.model)
    else:
        print(f"错误: {input_path} 不存在")

    print("\n完成")


if __name__ == "__main__":
    main()
