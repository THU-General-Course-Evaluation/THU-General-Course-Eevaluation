# 贡献指南

你可以通过提交 Issue 来贡献课程评价。提交后会由自动化流程生成结构化评价文件，并推送到批次分支。

## 提交方式

1. 在仓库中选择「新建 Issue」并选择「通识课评价」模板。
2. 填写课程号、课序号、评分与评价内容。
3. 提交后等待自动化流程推送到批次分支。

## 规范说明

- 评分范围：1-7
- 评分说明：分数越高表示越推荐，越低表示越不推荐
- 课程唯一标识：课程号-课序号
- 请尽量使用客观描述，避免人身攻击与不当言论。

## 维护者流程

1. 批量为需要处理的 Issue 添加 `course-review` 标签。
2. 等待 GitHub Actions 将生成结果提交到 `batch/course-review` 分支。
3. 将 `batch/course-review` 合并到 `main`。
4. 在 Actions 中手动触发 `Deploy MkDocs`（`workflow_dispatch`）完成部署。
5. 如果使用 Cloudflare Pages，可设置监听 `main` 分支自动构建（Build command: `uv sync --no-dev; uv run mkdocs build`，Output: `site`）。

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
