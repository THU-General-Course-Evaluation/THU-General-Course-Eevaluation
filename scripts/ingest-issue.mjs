import fs from "node:fs";
import path from "node:path";

const issueTitle = process.env.ISSUE_TITLE || "";
const issueBody = process.env.ISSUE_BODY || "";
const issueNumber = process.env.ISSUE_NUMBER || "";
const issueAuthor = process.env.ISSUE_AUTHOR || "";
const issueUrl = process.env.ISSUE_URL || "";

const dataPath = path.resolve("data", "courses.json");
const courses = JSON.parse(fs.readFileSync(dataPath, "utf-8"));

const fields = extractFields(issueBody);
const courseNo = fields["课程号"]?.trim();
const sectionNo = fields["课序号"]?.trim();
const rating = fields["评价打分（1-7）"]?.trim();
const content = fields["具体评价内容"]?.trim();

if (!courseNo || !sectionNo || !rating || !content) {
  throw new Error("缺少必填字段，请检查 Issue 模板填写情况。");
}

const ratingNum = Number(rating);
if (!Number.isInteger(ratingNum) || ratingNum < 1 || ratingNum > 7) {
  throw new Error("评分必须为 1-7 的整数。");
}

const course = courses.find(
  (item) => item.course_no === courseNo && item.section_no === sectionNo
);

if (!course) {
  throw new Error(`未在课程数据中找到 ${courseNo}-${sectionNo}。`);
}

const fileName = `${courseNo}-${sectionNo}.md`;
const filePath = path.resolve("docs", "courses", fileName);

const header = `# ${course.course_name}（${courseNo}-${sectionNo}）\n\n` +
  `- 开课院系：${course.dept}\n` +
  `- 学分：${course.credits}\n` +
  `- 主讲教师：${course.instructor}\n` +
  `- 上课时间：${course.schedule}\n` +
  `- 通识选修课组：${course.general_course_group}\n\n` +
  `## 学生评价\n\n`;

const reviewBlock = `### 评价 #${issueNumber}\n` +
  `- 评分：${ratingNum}/7\n` +
  `- 贡献者：@${issueAuthor}\n` +
  `- 来源：${issueUrl}\n` +
  `- 时间：${new Date().toISOString().slice(0, 10)}\n\n` +
  `${content}\n\n`;

if (!fs.existsSync(filePath)) {
  fs.writeFileSync(filePath, header + reviewBlock, "utf-8");
} else {
  const existing = fs.readFileSync(filePath, "utf-8");
  fs.writeFileSync(filePath, existing + reviewBlock, "utf-8");
}

console.log(`已生成或更新 ${filePath}`);

function extractFields(body) {
  const lines = body.split(/\r?\n/);
  const result = {};
  let currentKey = null;

  for (const line of lines) {
    const headingMatch = line.match(/^###\s+(.*)$/);
    if (headingMatch) {
      currentKey = headingMatch[1].trim();
      result[currentKey] = "";
      continue;
    }

    if (currentKey) {
      if (line.trim() === "") {
        if (result[currentKey].length > 0) {
          result[currentKey] += "\n";
        }
      } else {
        result[currentKey] += (result[currentKey] ? "\n" : "") + line.trim();
      }
    }
  }

  return result;
}
