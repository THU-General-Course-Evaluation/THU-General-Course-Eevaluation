"""根据 data/courses.json 生成两个独立的拼音索引页：

  docs/all-courses.md   —— 按课程名拼音
  docs/all-teachers.md  —— 按老师名拼音

各按首字母 A-Z 分组（其余归入 #）。只展示：课程名称、授课教师、课程号、课序号。
用法：uv run python scripts/build_course_catalog.py
"""

import json
from pathlib import Path

from pypinyin import lazy_pinyin

SOURCE = Path("data/courses.json")

# (表头, 字段) —— 按顺序渲染表格列。
COURSE_COLUMNS = [("课程名称", "course_name"), ("授课教师", "instructor"), ("课程号", "course_no"), ("课序号", "section_no")]
TEACHER_COLUMNS = [("授课教师", "instructor"), ("课程名称", "course_name"), ("课程号", "course_no"), ("课序号", "section_no")]


def cell(value: object) -> str:
    # 转义竖线，避免表格被课程名/教师名里的 | 撑破。
    return str(value or "").replace("|", "\\|")


def pinyin(text: str) -> str:
    return "".join(lazy_pinyin(text or "")).lower()


def first_letter(text: str) -> str:
    ch = (lazy_pinyin((text or "")[:1]) or [""])[0][:1].upper()
    return ch if "A" <= ch <= "Z" else "#"


def build_page(output: Path, title: str, courses: list[dict], sort_key, group_field: str, columns) -> None:
    ordered = sorted(courses, key=sort_key)
    groups: dict[str, list[dict]] = {}
    for course in ordered:
        groups.setdefault(first_letter(course.get(group_field, "")), []).append(course)
    letters = sorted(g for g in groups if g != "#")
    if "#" in groups:
        letters.append("#")

    header = "| " + " | ".join(h for h, _ in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [
        f"# {title}",
        "",
        f"共 {len(courses)} 门课程，按首字母分组（可用右侧目录跳转）。本页由脚本自动生成。",
        "",
    ]
    for letter in letters:
        lines += [f"## {letter}", "", header, divider]
        for course in groups[letter]:
            lines.append("| " + " | ".join(cell(course.get(f)) for _, f in columns) + " |")
        lines.append("")

    output.write_bytes(("\n".join(lines).rstrip("\n") + "\n").encode("utf-8"))
    print(f"已生成 {output}（{len(courses)} 门课程，{len(letters)} 组）")


def main() -> None:
    courses = json.loads(SOURCE.read_text(encoding="utf-8"))

    build_page(
        Path("docs/all-courses.md"),
        "全部课程（按课程名）",
        courses,
        sort_key=lambda c: (pinyin(c.get("course_name")), c.get("course_no", ""), c.get("section_no", "")),
        group_field="course_name",
        columns=COURSE_COLUMNS,
    )
    build_page(
        Path("docs/all-teachers.md"),
        "全部课程（按老师名）",
        courses,
        sort_key=lambda c: (pinyin(c.get("instructor")), pinyin(c.get("course_name")), c.get("course_no", ""), c.get("section_no", "")),
        group_field="instructor",
        columns=TEACHER_COLUMNS,
    )


if __name__ == "__main__":
    main()
