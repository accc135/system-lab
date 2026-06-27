import re
import csv
import json
import argparse
from pathlib import Path


def normalize_line(line: str) -> str:
    line = line.replace(" ", " ")
    line = line.replace("\t", " ")
    return line.strip()


def preprocess_lines(text: str) -> list[dict]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = text.split("\n")
    return [{"line_number": idx, "text": normalize_line(raw)} for idx, raw in enumerate(raw_lines, start=1)]


def split_paragraphs(lines: list[dict]) -> list[dict]:
    paragraphs = []
    current = []
    paragraph_id = 1

    for item in lines:
        if item["text"] == "":
            if current:
                paragraphs.append({
                    "paragraph_id": paragraph_id,
                    "start_line": current[0]["line_number"],
                    "lines": current
                })
                paragraph_id += 1
                current = []
        else:
            current.append(item)

    if current:
        paragraphs.append({
            "paragraph_id": paragraph_id,
            "start_line": current[0]["line_number"],
            "lines": current
        })

    return paragraphs


def is_item_marker(text: str) -> bool:
    text = text.strip()
    patterns = [
        r"^\d+、",
        r"^[一二三四五六七八九十]+、",
        r"^[（(]\d+[）)]",
        r"^[（(][一二三四五六七八九十]+[）)]",
    ]
    return any(re.match(p, text) for p in patterns)


def split_by_markers(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    marker_pattern = re.compile(
        r"\d+、|"
        r"[一二三四五六七八九十]+、|"
        r"[（(]\d+[）)]|"
        r"[（(][一二三四五六七八九十]+[）)]"
    )

    matches = list(marker_pattern.finditer(text))
    if not matches:
        return [text]

    results = []
    first_start = matches[0].start()
    if first_start > 0:
        prefix = text[:first_start].strip()
        if prefix:
            results.append(prefix)

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segment = text[start:end].strip()
        if segment:
            results.append(segment)

    return results


def split_by_punctuation(text: str, aggressive: bool = False) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    if aggressive:
        parts = re.split(r'(?<=[。！？；.!?;])\s*', text)
    else:
        parts = re.split(r'(?<=[。！？.!?])\s*', text)
    return [p.strip() for p in parts if p.strip()]


def build_char_line_map(line_entries: list[dict]) -> tuple[str, list[int]]:
    merged_parts = []
    char_to_line = []

    for item in line_entries:
        text = item["text"]
        if merged_parts:
            merged_parts.append(" ")
            char_to_line.append(item["line_number"])
        for ch in text:
            merged_parts.append(ch)
            char_to_line.append(item["line_number"])

    return "".join(merged_parts).strip(), char_to_line


def locate_segment(segment: str, merged: str, char_map: list[int], pos: int, default: int) -> tuple[int, int]:
    idx = merged.find(segment, pos)
    if idx == -1:
        idx = pos

    start = idx
    while start < len(merged) and merged[start].isspace():
        start += 1

    line = char_map[start] if start < len(char_map) else default
    return line, idx + len(segment)


def sentence_split(paragraph: dict, aggressive: bool = False) -> list[dict]:
    line_entries = paragraph["lines"]
    if not line_entries:
        return []

    merged, char_map = build_char_line_map(line_entries)
    if not merged:
        return []

    coarse = split_by_markers(merged)
    results = []
    pos = 0

    for seg in coarse:
        fine = split_by_punctuation(seg, aggressive=aggressive)

        if not aggressive and len(fine) >= 2 and is_item_marker(fine[0]):
            line, pos = locate_segment(seg, merged, char_map, pos, paragraph["start_line"])
            results.append({"line_number": line, "sentence_text": seg.strip()})
        else:
            for s in fine:
                if s.strip():
                    line, pos = locate_segment(s, merged, char_map, pos, paragraph["start_line"])
                    results.append({"line_number": line, "sentence_text": s.strip()})

    return results


def segment_policy(text: str, source_file: str, strategy: str = "conservative") -> list[dict]:
    lines = preprocess_lines(text)
    paragraphs = split_paragraphs(lines)

    aggressive = strategy == "aggressive"
    records = []
    sentence_id = 1

    for paragraph in paragraphs:
        for item in sentence_split(paragraph, aggressive=aggressive):
            s = re.sub(r"\s+", " ", item["sentence_text"]).strip()
            if s:
                records.append({
                    "source_file": source_file,
                    "sentence_id": sentence_id,
                    "paragraph_id": paragraph["paragraph_id"],
                    "line_number": item["line_number"],
                    "sentence_text": s
                })
                sentence_id += 1

    return records


def write_csv(records: list[dict], output_path: str):
    fields = ["source_file", "sentence_id", "paragraph_id", "line_number", "sentence_text"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def write_json(records: list[dict], output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="隐私政策文本分句工具")
    parser.add_argument("input_txt", help="输入 .txt 文件")
    parser.add_argument("--output", required=True, help="输出文件 (.csv 或 .json)")
    parser.add_argument("--strategy", choices=["conservative", "aggressive"], default="conservative")
    args = parser.parse_args()

    text = Path(args.input_txt).read_text(encoding="utf-8")
    records = segment_policy(text, Path(args.input_txt).name, strategy=args.strategy)

    if args.output.endswith(".json"):
        write_json(records, args.output)
    else:
        write_csv(records, args.output)

    print(f"完成: {len(records)} 条句子 -> {args.output}")


if __name__ == "__main__":
    main()
