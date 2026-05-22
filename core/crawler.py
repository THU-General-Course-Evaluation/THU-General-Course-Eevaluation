import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from lxml import html

BASE_URL = "https://zhjwxk.cic.tsinghua.edu.cn/xkBks.vxkBksJxjhBs.do"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="通识课选课信息抓取器")
    parser.add_argument("--output-dir", default="data/raw", help="输出目录")
    parser.add_argument("--max-pages", type=int, help="最大抓取页数")
    parser.add_argument("--from-file", help="从本地 HTML 文件解析（不发请求）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印请求信息")
    args = parser.parse_args()

    env = load_env()
    term = env.get("TERM", "2026-2027-1")
    first_token = env.get("TOKEN")

    if args.from_file:
        parse_local_file(Path(args.from_file), Path(args.output_dir))
        return

    jsessionid = resolve_jsessionid(env)
    if not jsessionid and not args.dry_run:
        raise SystemExit("未找到 JSESSIONID，请设置环境变量或提供 .env/cookies.txt")

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Referer": BASE_URL,
    }

    if args.dry_run:
        payload = build_payload(
            token=first_token,
            page=1,
            from_page=1,
            term=term,
        )
        print("[dry-run] URL:", BASE_URL)
        print("[dry-run] headers:", headers)
        print("[dry-run] payload:", payload)
        if jsessionid:
            print("[dry-run] cookie: JSESSIONID=***")
        return

    crawl_all_pages(
        jsessionid=jsessionid,
        token=first_token,
        term=term,
        output_dir=Path(args.output_dir),
        max_pages=args.max_pages,
        headers=headers,
    )


def build_payload(token: str | None, page: int, from_page: int, term: str):
    payload = {
        "m": (None, "kkxxSearch"),
        "p_sort.asc1": (None, "true"),
        "p_sort.asc2": (None, "true"),
        "pathContent": (None, "%D2%BB%BC%B6%BF%CE%BF%AA%BF%CE%D0%C5%CF%A2"),
        "p_xnxq": (None, term),
        "page": (None, str(page)),
        "goPageNumber": (None, str(from_page)),
    }
    if token:
        payload["token"] = (None, token)
    return payload


def parse_html(content: str):
    tree = html.fromstring(content)
    token_nodes = tree.xpath("//input[@name='token']/@value")
    token = token_nodes[0] if token_nodes else None
    records = extract_records(tree)
    total_pages = extract_total_pages(tree)
    return token, total_pages, records


def extract_total_pages(tree) -> int | None:
    end_link = tree.xpath("//a[@id='endpage']/@href")
    if end_link:
        match = re.search(r"turn\((\d+)\)", end_link[0])
        if match:
            return int(match.group(1))

    page_text = " ".join(tree.xpath("//p[contains(@class, 'yeM')]//text()"))
    match = re.search(r"共\s*([\d,]+)\s*页", page_text)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def extract_records(tree) -> list[dict[str, str]]:
    headers = [
        "dept",
        "course_no",
        "section_no",
        "course_name",
        "credits",
        "instructor",
        "ug_capacity",
        "ug_remaining",
        "grad_capacity",
        "grad_remaining",
        "schedule",
        "selection_note",
        "course_features",
        "grade",
        "secondary_selection",
        "lab_info",
        "repeat_counts",
        "selection_limit",
        "general_course_group",
    ]
    records = []
    rows = tree.xpath("//table//tr[@class='trr2']")
    for row in rows:
        cells = row.xpath("./td")
        values = [normalize_text(cell) for cell in cells]
        if len(values) < len(headers):
            continue
        record = dict(zip(headers, values[: len(headers)], strict=False))
        records.append(record)
    return records


def normalize_text(cell) -> str:
    text = " ".join(cell.xpath(".//text()"))
    return re.sub(r"\s+", " ", text).strip()


def crawl_all_pages(
    jsessionid: str,
    token: str | None,
    term: str,
    output_dir: Path,
    max_pages: int | None,
    headers: dict[str, str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "pages"
    temp_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    resume_state = resolve_resume_state(output_dir, temp_dir)
    current_page = resume_state.start_page
    total_pages = resume_state.total_pages
    current_token = resume_state.token or token

    target_pages = total_pages
    if max_pages and total_pages:
        target_pages = min(total_pages, max_pages)

    while True:
        if total_pages and current_page > total_pages:
            break
        if current_page > 1 and not current_token:
            raise SystemExit("缺少翻页 token，无法继续请求。")

        page_json = temp_dir / f"page-{current_page:04d}.json"
        page_html = temp_dir / f"page-{current_page:04d}.html"
        if page_json.exists():
            records = json.loads(page_json.read_text(encoding="utf-8"))
            next_token = current_token
            detected_total = total_pages
        else:
            content = fetch_page(
                session=session,
                jsessionid=jsessionid,
                page=current_page,
                from_page=max(1, current_page - 1),
                term=term,
                token=current_token,
                headers=headers,
            )

            next_token, detected_total, records = parse_html(content)
            page_html.write_text(content, encoding="utf-8")
            page_json.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if total_pages is None and detected_total:
            total_pages = detected_total
            if max_pages:
                target_pages = min(total_pages, max_pages)

        total_label = target_pages or total_pages or "?"
        print(
            f"已保存: {page_json} ({len(records)} 条记录) "
            f"[{current_page}/{total_label}]"
        )

        if total_pages is None:
            total_pages = current_page

        if max_pages and current_page >= max_pages:
            break
        if current_page >= total_pages:
            break

        current_page += 1
        current_token = next_token

    merge_pages(temp_dir, output_dir)


def fetch_page(
    session: requests.Session,
    jsessionid: str,
    page: int,
    from_page: int,
    term: str,
    token: str | None,
    headers: dict[str, str],
) -> str:
    payload = build_payload(
        token=token,
        page=page,
        from_page=from_page,
        term=term,
    )
    response = session.post(
        BASE_URL,
        files=payload,
        headers=headers,
        cookies={"JSESSIONID": jsessionid},
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = "gbk"
    return response.text


def parse_local_file(path: Path, output_dir: Path) -> None:
    content = path.read_text(encoding="utf-8")
    token, total_pages, records = parse_html(content)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = output_dir / f"example-{timestamp}.json"
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"解析完成: {path}")
    print(f"token: {token}")
    print(f"total_pages: {total_pages}")
    print(f"records: {len(records)}")


def merge_pages(temp_dir: Path, output_dir: Path) -> None:
    page_files = resolve_page_json_files(output_dir, temp_dir)
    all_records: list[dict[str, str]] = []
    for file_path in page_files:
        try:
            items = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(items, list):
            all_records.extend(items)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    merged_path = output_dir / f"records-{timestamp}.json"
    merged_path.write_text(
        json.dumps(all_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已合并输出: {merged_path} ({len(all_records)} 条记录)")


class ResumeState:
    def __init__(self, start_page: int, token: str | None, total_pages: int | None) -> None:
        self.start_page = start_page
        self.token = token
        self.total_pages = total_pages


def resolve_resume_state(output_dir: Path, temp_dir: Path) -> ResumeState:
    legacy_html = list(output_dir.glob("page-*-*.html"))
    temp_html = list(temp_dir.glob("page-*.html"))
    candidates = legacy_html + temp_html
    if not candidates:
        return ResumeState(start_page=1, token=None, total_pages=None)

    latest_by_page: dict[int, Path] = {}
    for path in candidates:
        page = extract_page_number(path.name)
        if page is None:
            continue
        existing = latest_by_page.get(page)
        if existing is None or path.stat().st_mtime > existing.stat().st_mtime:
            latest_by_page[page] = path

    last_page = max(latest_by_page.keys())
    last_html = latest_by_page[last_page]
    content = last_html.read_text(encoding="utf-8", errors="ignore")
    token, total_pages, _ = parse_html(content)
    return ResumeState(start_page=last_page + 1, token=token, total_pages=total_pages)


def resolve_page_json_files(output_dir: Path, temp_dir: Path) -> list[Path]:
    legacy_json = list(output_dir.glob("page-*-*.json"))
    temp_json = list(temp_dir.glob("page-*.json"))
    latest_by_page: dict[int, Path] = {}

    for path in legacy_json + temp_json:
        page = extract_page_number(path.name)
        if page is None:
            continue
        existing = latest_by_page.get(page)
        if existing is None or path.stat().st_mtime > existing.stat().st_mtime:
            latest_by_page[page] = path

    return [latest_by_page[key] for key in sorted(latest_by_page.keys())]


def extract_page_number(filename: str) -> int | None:
    match = re.search(r"page-(\d+)", filename)
    if not match:
        return None
    return int(match.group(1))


def load_env() -> dict[str, str]:
    env_path = Path(".env")
    if not env_path.exists():
        return {}
    result = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        result[key.strip()] = value.strip().strip('"')
    return result


def resolve_jsessionid(env: dict[str, str]) -> str | None:
    env_value = env.get("JSESSIONID") or os.getenv("JSESSIONID")
    if env_value:
        return env_value.strip()

    cookie_path = Path("cookies.txt")
    if cookie_path.exists():
        for line in cookie_path.read_text(encoding="utf-8").splitlines():
            if "JSESSIONID" in line:
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "JSESSIONID":
                        return value.strip()
                parts = line.split("\t")
                if len(parts) >= 7 and parts[5] == "JSESSIONID":
                    return parts[6].strip()

    return None


if __name__ == "__main__":
    main()
