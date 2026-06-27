import json
import csv
import argparse
import numpy as np
from pathlib import Path


POSITIVE_KEYWORDS = [
    "收集", "采集", "获取", "获得", "读取", "提取",
    "使用", "利用", "处理", "分析", "统计", "挖掘", "画像",
    "存储", "保存", "留存", "记录",
    "共享", "分享", "传输", "传递", "转让", "提供给", "披露", "公开",
    "对外提供", "第三方",
    "个人信息", "个人数据", "隐私", "敏感信息",
    "姓名", "身份证", "手机号", "电话", "邮箱", "地址",
    "位置信息", "地理位置", "定位", "GPS",
    "设备信息", "设备标识", "IMEI", "IDFA", "MAC地址", "IP地址",
    "浏览记录", "搜索记录", "日志", "Cookie",
    "人脸", "面部", "指纹", "生物", "声纹",
    "通讯录", "好友", "联系人",
    "交易", "订单", "支付", "账号",
    "简历", "身份信息", "实名",
    "推荐", "推送", "个性化", "广告", "营销", "投放",
    "授权", "权限", "同意",
    "SDK", "第三方",
]

NEGATIVE_KEYWORDS = [
    "不可抗力", "免责", "赔偿责任",
    "知识产权", "著作权", "商标",
    "管辖", "仲裁", "诉讼",
    "用户行为规范", "禁止",
    "服务变更", "服务中断", "服务终止",
    "违法", "违规",
]


def load_sentences(json_paths: list[str]) -> list[dict]:
    all_records = []
    for path in json_paths:
        with open(path, "r", encoding="utf-8") as f:
            all_records.extend(json.load(f))
    return all_records


def keyword_score(text: str) -> float:
    score = 0
    lower = text.lower()
    for kw in POSITIVE_KEYWORDS:
        if kw.lower() in lower:
            score += 1
    for kw in NEGATIVE_KEYWORDS:
        if kw.lower() in lower:
            score -= 2
    return score


def compute_embeddings(texts: list[str], model_name: str):
    from sentence_transformers import SentenceTransformer
    print(f"加载模型 {model_name} ...")
    model = SentenceTransformer(model_name)
    print(f"计算 {len(texts)} 条句子向量...")
    return model.encode(texts, show_progress_bar=True, batch_size=64)


def compute_tfidf(texts: list[str]):
    import jieba
    from sklearn.feature_extraction.text import TfidfVectorizer
    print("使用 jieba + TF-IDF 生成特征...")
    tokenized = [" ".join(jieba.cut(t)) for t in texts]
    vectorizer = TfidfVectorizer(max_features=5000)
    return vectorizer.fit_transform(tokenized).toarray()


def classify(records: list[dict], n_clusters: int = 10,
             model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
             use_tfidf: bool = False) -> list[dict]:
    from sklearn.cluster import KMeans

    texts = [r["sentence_text"] for r in records]
    min_len = 5
    valid_mask = [len(t) >= min_len for t in texts]
    valid_records = [r for r, v in zip(records, valid_mask) if v]
    valid_texts = [t for t, v in zip(texts, valid_mask) if v]
    short_records = [r for r, v in zip(records, valid_mask) if not v]

    if use_tfidf:
        embeddings = compute_tfidf(valid_texts)
    else:
        embeddings = compute_embeddings(valid_texts, model_name)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    cluster_labels = {}
    for cid in range(n_clusters):
        indices = np.where(labels == cid)[0]
        scores = [keyword_score(valid_records[i]["sentence_text"]) for i in indices]
        avg = np.mean(scores) if scores else 0
        cluster_labels[cid] = "是" if avg >= 2.0 else "否"

    results = []
    for i, r in enumerate(valid_records):
        results.append({**r, "cluster_id": int(labels[i]),
                        "is_personal_info_related": cluster_labels[labels[i]]})
    for r in short_records:
        results.append({**r, "cluster_id": -1, "is_personal_info_related": "否"})

    results.sort(key=lambda x: (x["source_file"], x["sentence_id"]))
    return results


def main():
    parser = argparse.ArgumentParser(description="基于聚类的隐私政策句子分类")
    parser.add_argument("inputs", nargs="+", help="分句 JSON 文件")
    parser.add_argument("--output", default="classification_result.csv")
    parser.add_argument("--n-clusters", type=int, default=10)
    parser.add_argument("--use-tfidf", action="store_true")
    args = parser.parse_args()

    records = load_sentences(args.inputs)
    print(f"加载 {len(records)} 条句子")

    results = classify(records, n_clusters=args.n_clusters, use_tfidf=args.use_tfidf)

    fields = ["source_file", "sentence_id", "paragraph_id", "line_number",
              "sentence_text", "cluster_id", "is_personal_info_related"]

    if args.output.endswith(".json"):
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    else:
        with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(results)

    related = sum(1 for r in results if r["is_personal_info_related"] == "是")
    print(f"完成: {len(results)} 条 | 相关 {related} | 无关 {len(results) - related}")


if __name__ == "__main__":
    main()
