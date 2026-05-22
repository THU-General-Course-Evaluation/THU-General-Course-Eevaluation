"""合并多个 records-*.json，按 (课程号, 课序号) 去重，生成 data/courses.json。

用法：
    uv run python scripts/build_courses.py
    uv run python scripts/build_courses.py data/records-1.json data/records-2.json
"""

import json
import sys
from pathlib import Path

DEFAULT_INPUTS = ["data/records-1.json", "data/records-2.json"]
OUTPUT = Path("data/courses.json")


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"找不到输入文件：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit(f"{path} 不是 JSON 数组")
    return data


def main(argv: list[str]) -> None:
    inputs = [Path(p) for p in (argv or DEFAULT_INPUTS)]

    merged: dict[tuple[str, str], dict] = {}
    total = 0
    for path in inputs:
        records = load_records(path)
        total += len(records)
        for record in records:
            # 后出现的文件覆盖先出现的（较新快照优先）。
            key = (record.get("course_no", ""), record.get("section_no", ""))
            merged[key] = record

    courses = [merged[key] for key in sorted(merged)]
    OUTPUT.write_bytes(
        (json.dumps(courses, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    print(
        f"输入 {total} 条（{len(inputs)} 个文件），去重后 {len(courses)} 条"
        f"（去掉 {total - len(courses)} 个重复）→ {OUTPUT}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
