import json
import os
import re
from datetime import datetime
from pathlib import Path

from pypinyin import lazy_pinyin

ROOT_DIR = Path(__file__).resolve().parents[1]
COURSE_DATA_PATH = ROOT_DIR / "data" / "courses.json"
COURSE_DOCS_DIR = ROOT_DIR / "docs" / "courses"
COURSE_INDEX_PATH = COURSE_DOCS_DIR / "index.md"

REQUIRED_FIELDS = ["课程号", "课序号", "评价打分（1-7）", "具体评价内容"]


def main() -> None:
    issue_body = os.getenv("ISSUE_BODY", "")
    issue_number = os.getenv("ISSUE_NUMBER", "")
    issue_author = os.getenv("ISSUE_AUTHOR", "")
    issue_url = os.getenv("ISSUE_URL", "")

    fields = parse_issue_body(issue_body)
    validate_fields(fields)

    course_no = fields["课程号"].strip()
    section_no = fields["课序号"].strip()
    rating = parse_rating(fields["评价打分（1-7）"])
    content = fields["具体评价内容"].strip()

    course = find_course(course_no, section_no)
    if not course:
        raise SystemExit(f"未在课程数据中找到 {course_no}-{section_no}。")

    course_file = COURSE_DOCS_DIR / f"{course_no}-{section_no}.md"
    write_or_append_review(
        course=course,
        course_no=course_no,
        section_no=section_no,
        rating=rating,
        content=content,
        issue_number=issue_number,
        issue_author=issue_author,
        issue_url=issue_url,
        path=course_file,
    )

    update_index()



def parse_issue_body(body: str) -> dict[str, str]:
    lines = body.splitlines()
    result: dict[str, str] = {}
    current_key = None

    for line in lines:
        heading = re.match(r"^###\s+(.*)$", line)
        if heading:
            current_key = heading.group(1).strip()
            result[current_key] = ""
            continue

        if current_key is not None:
            if line.strip() == "":
                if result[current_key]:
                    result[current_key] += "\n"
            else:
                result[current_key] += ("\n" if result[current_key] else "") + line.strip()

    return result



def validate_fields(fields: dict[str, str]) -> None:
    missing = [key for key in REQUIRED_FIELDS if not fields.get(key, "").strip()]
    if missing:
        raise SystemExit(f"缺少必填字段: {', '.join(missing)}")



def parse_rating(value: str) -> int:
    value = value.strip()
    if not value.isdigit():
        raise SystemExit("评分必须为 1-7 的整数。")
    rating = int(value)
    if rating < 1 or rating > 7:
        raise SystemExit("评分必须为 1-7 的整数。")
    return rating



def find_course(course_no: str, section_no: str) -> dict | None:
    courses = json.loads(COURSE_DATA_PATH.read_text(encoding="utf-8"))
    for course in courses:
        if course.get("course_no") == course_no and course.get("section_no") == section_no:
            return course
    return None



def write_or_append_review(
    course: dict,
    course_no: str,
    section_no: str,
    rating: int,
    content: str,
    issue_number: str,
    issue_author: str,
    issue_url: str,
    path: Path,
) -> None:
    COURSE_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    header = (
        f"# {course.get('course_name', '')}（{course_no}-{section_no}）\n\n"
        f"- 开课院系：{course.get('dept', '')}\n"
        f"- 学分：{course.get('credits', '')}\n"
        f"- 主讲教师：{course.get('instructor', '')}\n"
        f"- 上课时间：{course.get('schedule', '')}\n"
        f"- 通识选修课组：{course.get('general_course_group', '')}\n\n"
        "## 学生评价\n\n"
    )

    review_block = (
        f"### 评价 #{issue_number}\n"
        f"- 评分：{rating}/7\n"
        f"- 贡献者：@{issue_author}\n"
        f"- 来源：{issue_url}\n"
        f"- 时间：{datetime.now().strftime('%Y-%m-%d')}\n\n"
        f"{content}\n\n"
    )

    if not path.exists():
        path.write_text(header + review_block, encoding="utf-8")
        return

    existing = path.read_text(encoding="utf-8")
    if "## 学生评价" not in existing:
        existing = existing.strip() + "\n\n## 学生评价\n\n"
    path.write_text(
        upsert_review_block(existing, issue_number, review_block), encoding="utf-8"
    )


def upsert_review_block(existing: str, issue_number: str, review_block: str) -> str:
    """同号评价已存在则原地覆盖，否则追加到末尾。"""
    pattern = re.compile(
        rf"(?ms)^### 评价 #{re.escape(issue_number)}\n.*?(?=^### |^## |\Z)"
    )
    if pattern.search(existing):
        return pattern.sub(lambda _: review_block, existing, count=1)
    return existing + review_block



def update_index() -> None:
    COURSE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    course_files = sorted(
        [path for path in COURSE_DOCS_DIR.glob("*.md") if path.name != "index.md"],
        key=lambda path: path.name,
    )

    courses = json.loads(COURSE_DATA_PATH.read_text(encoding="utf-8"))
    course_map = {
        f"{course.get('course_no')}-{course.get('section_no')}": course
        for course in courses
    }

    rows = []
    for path in course_files:
        key = path.stem
        course = course_map.get(key, {})
        ratings = extract_ratings(path.read_text(encoding="utf-8"))
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        rows.append(
            {
                "course_name": course.get("course_name", key),
                "key": key,
                "instructor": course.get("instructor", ""),
                "group": course.get("general_course_group", ""),
                "avg": f"{avg_rating:.2f}" if avg_rating is not None else "-",
                "count": str(len(ratings)),
            }
        )

    lines = [
        "# 课程评价",
        "",
        "此页面由 GitHub Actions 自动生成。",
        "",
    ]

    lines.extend(render_section("按课程名称排序（拼音）", sort_by_name(rows)))
    lines.extend(render_group_sections("按通识课组排序", rows))
    lines.extend(render_section("按推荐度排序", sort_by_rating(rows)))
    lines.extend(render_section("按老师姓名排序（拼音）", sort_by_instructor(rows)))

    COURSE_INDEX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")



def extract_ratings(content: str) -> list[int]:
    ratings = []
    for match in re.finditer(r"评分：\s*(\d)\s*/\s*7", content):
        ratings.append(int(match.group(1)))
    return ratings


def render_section(title: str, items: list[dict[str, str]]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| 课程 | 课程号-课序号 | 主讲教师 | 通识课组 | 平均评分 | 评价数 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        link = f"[{item['course_name']}]({item['key']}.md)"
        lines.append(
            f"| {link} | {item['key']} | {item['instructor']} | {item['group']} | {item['avg']} | {item['count']} |"
        )
    lines.append("")
    return lines


def sort_by_name(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda item: to_pinyin(item["course_name"]))


def sort_by_instructor(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda item: to_pinyin(item["instructor"]))


def sort_by_rating(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    def rating_key(item: dict[str, str]) -> float:
        try:
            return float(item["avg"])
        except ValueError:
            return -1.0

    return sorted(rows, key=rating_key, reverse=True)


def sort_by_group(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    order = {"人文": 1, "社科": 2, "艺术": 3, "科学": 4}

    def group_key(item: dict[str, str]):
        group = item["group"] or ""
        prefix = ""
        for key in order:
            if group.startswith(key):
                prefix = key
                break
        return (order.get(prefix, 99), to_pinyin(item["course_name"]))

    return sorted(rows, key=group_key)


def to_pinyin(value: str) -> str:
    if not value:
        return ""
    return "".join(lazy_pinyin(value))


def render_group_sections(title: str, rows: list[dict[str, str]]) -> list[str]:
    group_order = ["科学课组", "人文课组", "社科课组", "艺术课组"]
    lines = [f"## {title}", ""]

    for group in group_order:
        group_rows = [item for item in rows if item["group"].startswith(group)]
        group_rows = sorted(group_rows, key=lambda item: to_pinyin(item["course_name"]))
        lines.append(f"### {group}")
        lines.append("")
        lines.extend(render_section_table(group_rows))
        lines.append("")

    return lines


def render_section_table(items: list[dict[str, str]]) -> list[str]:
    lines = [
        "| 课程 | 课程号-课序号 | 主讲教师 | 通识课组 | 平均评分 | 评价数 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in items:
        link = f"[{item['course_name']}]({item['key']}.md)"
        lines.append(
            f"| {link} | {item['key']} | {item['instructor']} | {item['group']} | {item['avg']} | {item['count']} |"
        )
    return lines


if __name__ == "__main__":
    main()
