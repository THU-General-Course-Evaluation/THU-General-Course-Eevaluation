# 通识课课程评价

面向通识课的课程质量评价平台，基于 Markdown + MkDocs Material 构建静态站点，并通过 Issue 自动生成课程评价。

## 站点展示

- GitHub Pages：启用后自动部署到 `https://<your-username>.github.io/general-course-evaluation/`
- Cloudflare Pages：可直接以本仓库为源，构建命令 `mkdocs build`，输出目录 `site/`

## 贡献方式

- 提交 Issue（使用「通识课评价」模板）
- 维护者批量添加 `course-review` 标签后触发自动化流程
- 生成内容提交到批次分支 `batch/course-review`
- 维护者合并该分支到 `main` 后手动触发部署

评分范围为 1-7，分数越高表示越推荐，越低表示越不推荐。

## 本地预览

```pwsh
uv sync --no-dev
uv run mkdocs serve
```

## 课程数据

课程数据位于 `data/courses.json`，用于匹配课程号与课序号。字段示例：

- `dept`：开课院系
- `course_no`：课程号
- `section_no`：课序号
- `course_name`：课程名
- `credits`：学分
- `instructor`：主讲教师
- `ug_capacity` / `ug_remaining`
- `grad_capacity` / `grad_remaining`
- `schedule`：上课时间
- `selection_note`：选课文字说明
- `course_features`：课程特色
- `grade`：年级
- `secondary_selection`：是否二级选课
- `lab_info`：实验信息
- `repeat_counts`：重修是否占容量
- `selection_limit`：是否选课时限制
- `general_course_group`：通识选修课组

## 课程数据抓取

- 抓取脚本：`core/crawler.py`
- 环境变量：复制 `.env.example` 为 `.env`，填入 `JSESSIONID`、`TOKEN`、`TERM`
- 抓取命令：

```pwsh
uv run python -m core.crawler
```

- 输出位置：
	- 分页 JSON：`data/raw/pages/page-XXXX.json`
	- 合并结果：`data/raw/records-YYYYMMDD-HHMMSS.json`

## 自动化流程

- `issues` 触发：带有 `course-review` 标签的 Issue 触发 `github-action/ingest_issue.py`
- 生成或追加 `docs/courses/{课程号}-{课序号}.md`，并更新 `docs/courses/index.md`
- 自动提交到 `batch/course-review`，维护者合并后手动触发 `workflow_dispatch` 部署
- Cloudflare Pages：可配置为监听 `main` 分支自动构建（Build command: `uv sync --no-dev; uv run mkdocs build`，Output: `site`）
