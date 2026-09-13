#!/usr/bin/env python3
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "else", "for", "to", "of", "in",
    "on", "at", "with", "from", "by", "is", "it", "as", "be", "was", "were", "are", "this",
    "that", "these", "those", "you", "your", "we", "our", "us", "i", "me", "my", "mine",
    "he", "she", "they", "them", "their", "his", "her", "its", "do", "does", "did", "have",
    "has", "had", "not", "no", "yes", "can", "could", "would", "should", "will", "just",
    "about", "after", "before", "into", "out", "over", "under", "up", "down", "too", "very",
    "also", "what", "when", "where", "why", "how", "who", "which", "there", "here", "all",
    "some", "any", "more", "most", "other", "much", "many", "so", "than", "then", "them",
    "sorry", "thanks", "thank", "hello", "hi", "hey"
}


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze exported WeChat chat history files.")
    parser.add_argument("--input-folder", required=True, help="Folder containing exported chat .txt files")
    parser.add_argument("--output-dir", default="wechat_analysis_output", help="Folder for CSV/JSON reports")
    parser.add_argument("--max-files", type=int, default=200, help="Maximum number of files to scan")
    return parser.parse_args()


def add_to_output_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def looks_like_date(value):
    value = value.strip()
    return bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", value))


def normalize_datetime(raw):
    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M",
        "%Y/%m/%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S %z",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    return None


def extract_message(line):
    text = line.strip()
    if not text:
        return None

    patterns = [
        r'^(?P<dt>\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?)\s*(?:\[(?P<sender>[^\]]+)\]\s*)?(?P<body>.*)$',
        r'^(?P<dt>\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(?:[:.]\d+)?)\s*[,\-]\s*(?P<sender>[^:]+):\s*(?P<body>.*)$',
        r'^(?P<dt>\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?)\s+(?P<sender>[^:]+):\s*(?P<body>.*)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, text)
        if match:
            dt = match.group("dt")
            sender = (match.group("sender") or "Unknown").strip()
            body = (match.group("body") or "").strip()
            if body:
                return {
                    "timestamp": dt,
                    "sender": sender,
                    "message": body,
                }

    if "\t" in text:
        parts = [p.strip() for p in text.split("\t") if p.strip()]
        if len(parts) >= 3 and looks_like_date(parts[0]):
            return {
                "timestamp": parts[0],
                "sender": parts[1],
                "message": "\t".join(parts[2:]),
            }

    if "," in text:
        left, sep, right = text.partition(",")
        if looks_like_date(left) and ":" in right:
            sender, msg = right.split(":", 1)
            return {"timestamp": left, "sender": sender.strip(), "message": msg.strip()}

    return None


def tokenize_text(message):
    # Keeps Chinese characters and standard words together.
    tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", message)
    cleaned = []
    for token in tokens:
        lower = token.lower()
        if lower not in STOPWORDS:
            cleaned.append(lower)
    return cleaned


def summarize(records):
    if not records:
        return {
            "total_messages": 0,
            "unique_senders": 0,
            "top_senders": [],
            "top_days": [],
            "top_hours": [],
            "top_words": [],
            "average_message_length": 0.0,
            "total_words": 0,
        }

    sender_counts = Counter(r["sender"] for r in records)
    day_counts = Counter(r["dt"].strftime("%Y-%m-%d") for r in records if r.get("dt"))
    hour_counts = Counter(r["dt"].strftime("%H:00") for r in records if r.get("dt"))

    word_counter = Counter()
    message_lengths = []
    for record in records:
        msg = record["message"]
        message_lengths.append(len(msg))
        word_counter.update(tokenize_text(msg))

    summary = {
        "total_messages": len(records),
        "unique_senders": len(sender_counts),
        "top_senders": sender_counts.most_common(10),
        "top_days": day_counts.most_common(10),
        "top_hours": hour_counts.most_common(10),
        "top_words": word_counter.most_common(20),
        "average_message_length": round(sum(message_lengths) / len(message_lengths), 2) if message_lengths else 0.0,
        "total_words": sum(word_counter.values()),
    }
    return summary


def discover_chat_files(folder: Path, limit: int):
    files = []
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".txt", ".csv", ".json"}:
            files.append(path)
            if len(files) >= limit:
                break
    return files


def parse_chat_file(file_path: Path):
    records = []
    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parsed = extract_message(line)
            if not parsed:
                continue
            dt = normalize_datetime(parsed["timestamp"])
            if dt is None:
                continue
            records.append({
                "timestamp": parsed["timestamp"],
                "sender": parsed["sender"],
                "message": parsed["message"],
                "dt": dt,
            })
    return records


def write_csv(data, output_path):
    fieldnames = ["timestamp", "sender", "message", "date", "hour", "weekday"]
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow({
                "timestamp": row["timestamp"],
                "sender": row["sender"],
                "message": row["message"],
                "date": row["dt"].strftime("%Y-%m-%d"),
                "hour": row["dt"].strftime("%H:00"),
                "weekday": row["dt"].strftime("%A"),
            })


def write_summary(summary, output_path):
    lines = [
        "WeChat chat analysis summary",
        "=" * 28,
        f"Total messages: {summary['total_messages']}",
        f"Unique senders: {summary['unique_senders']}",
        f"Average message length: {summary['average_message_length']}",
        f"Total words: {summary['total_words']}",
        "",
        "Top senders:",
    ]
    for sender, count in summary["top_senders"]:
        lines.append(f"- {sender}: {count}")

    lines.extend(["", "Top days:"])
    for day, count in summary["top_days"]:
        lines.append(f"- {day}: {count}")

    lines.extend(["", "Top hours:"])
    for hour, count in summary["top_hours"]:
        lines.append(f"- {hour}: {count}")

    lines.extend(["", "Top words:"])
    for word, count in summary["top_words"]:
        lines.append(f"- {word}: {count}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_json(data, summary, output_path):
    payload = {"summary": summary, "messages": data}
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    args = parse_args()
    input_folder = Path(args.input_folder)
    output_dir = Path(args.output_dir)
    add_to_output_dir(str(output_dir))

    if not input_folder.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

    files = discover_chat_files(input_folder, args.max_files)
    if not files:
        raise FileNotFoundError(f"No .txt/.csv/.json files found in {input_folder}")

    all_records = []
    for file_path in files:
        all_records.extend(parse_chat_file(file_path))

    summary = summarize(all_records)
    write_csv(all_records, output_dir / "wechat_messages.csv")
    write_summary(summary, output_dir / "wechat_summary.txt")
    export_json(all_records, summary, output_dir / "wechat_analysis.json")

    print(f"Scanned {len(files)} files")
    print(f"Parsed {len(all_records)} messages")
    print(f"Summary written to {output_dir}")
    print(json.dumps({
        "total_messages": summary["total_messages"],
        "unique_senders": summary["unique_senders"],
        "top_sender": summary["top_senders"][0] if summary["top_senders"] else None,
        "top_word": summary["top_words"][0] if summary["top_words"] else None,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
