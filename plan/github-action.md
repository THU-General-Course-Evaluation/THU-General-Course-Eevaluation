# GitHub Actions 设计记录

## 校验与报错
- GitHub Actions 需要先检验 Issue/PR 是否符合格式。
- 未通过校验时，应在对应 Issue/PR 下显示错误信息。
- 已实现：失败时自动评论并阻断提交。

## 生成流程
- 对于校验通过的内容：
  - 从课程信息 JSON 中匹配课程。
  - 创建或追加到 Markdown 评价文档。
  - 同步更新索引页面（见 `plan/demonstration.md`）。
  - 更新评价等级等聚合信息。
  - 自动提交到批次分支 `batch/course-review`，由维护者合并后手动部署。
