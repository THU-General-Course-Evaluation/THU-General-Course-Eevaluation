# 核心设计记录

## 状态
- 已完成（2026-05-22）
- 已实现：uv 环境管理、爬虫（GBK/UTF-8 解析）、断点续抓、按页存储与合并输出

## Python 环境
- 使用 `uv` 管理 Python 依赖与环境。
- GitHub Actions 中同样使用 `uv` 安装依赖与运行构建。

## 选课信息获取
- 需要进一步确定如何获取学校的官方选课信息。
- 明确数据获取渠道、更新频率与数据合法合规性。

### 抓取方案（待验证）
- url: https://zhjwxk.cic.tsinghua.edu.cn/xkBks.vxkBksJxjhBs.do
- method: POST
- Headers:
	- Content-Type: multipart/form-data
	- User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0
	- Referer: https://zhjwxk.cic.tsinghua.edu.cn/xkBks.vxkBksJxjhBs.do
	- Cookie: JSESSIONID=aeh3p_qVkN97d8sAEPp5z（运行前需要手动更新，可从 `.env` 或 `cookies.txt` 读取）
- payload（multipart form-data）:
	- m: kkxxSearch
	- p_sort.asc1: true
	- p_sort.asc2: true
	- pathContent: %D2%BB%BC%B6%BF%CE%BF%AA%BF%CE%D0%C5%CF%A2
	- p_xnxq: 2026-2027-1
	- page: 2（表示需要前往的 page）
	- goPageNumber: 1（表示从哪个 page 来的）
	- token: 089a4195c5217e3060591e5046344194（每次请求一页后返回的 html 中包含新 token，用于请求下一页）
