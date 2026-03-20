# Playwright E2E 环境搭建指南

这份文档总结了当前仓库在另一台机器上搭建 Playwright E2E 验证环境的完整过程，目标是做到：

- 启动本地服务到 `http://127.0.0.1:3000`
- 用 Playwright 打开页面
- 自动收集 `console`、页面异常、失败请求和异常响应
- 复用在“登录/鉴权按钮点击后检查报错”这类验证场景里

## 适用项目

当前项目不是独立的 Node 前端工程，而是：

- 后端：FastAPI
- 前端：仓库内的静态页面 [`web/index.html`](/Users/cx/cx/obsidian_search/web/index.html)
- 启动脚本：[`scripts/start.sh`](/Users/cx/cx/obsidian_search/scripts/start.sh)

因此 Playwright 的职责不是“启动前端构建工具”，而是：

1. 启动 Python Web 服务
2. 打开页面
3. 执行浏览器侧验证

## 前置条件

目标机器需要具备：

- `node` 和 `npm`
- `python3`
- 可正常启动项目的 Python 依赖环境

本机验证时使用的是：

- `node v24.7.0`
- `npm 11.5.1`

可用以下命令检查：

```bash
node -v
npm -v
python3 --version
```

## 项目内新增的文件

为了支持 E2E，仓库新增了这些文件：

- [`package.json`](/Users/cx/cx/obsidian_search/package.json)
- [`playwright.config.js`](/Users/cx/cx/obsidian_search/playwright.config.js)
- [`tests/e2e/smoke.spec.js`](/Users/cx/cx/obsidian_search/tests/e2e/smoke.spec.js)
- [`tests/e2e/README.md`](/Users/cx/cx/obsidian_search/tests/e2e/README.md)

## 一次性安装步骤

在仓库根目录执行：

```bash
npm install -D @playwright/test
```

然后安装 Playwright 浏览器：

```bash
npm run e2e:install
```

这一步会下载：

- Chromium
- Playwright 运行所需的附加组件

## package.json 脚本

当前脚本定义如下：

```json
{
  "scripts": {
    "start:web": "OBS_BIND_PORT=3000 ./scripts/start.sh",
    "e2e": "playwright test",
    "e2e:headed": "playwright test --headed",
    "e2e:ui": "playwright test --ui",
    "e2e:install": "playwright install chromium"
  }
}
```

含义如下：

- `npm run start:web`
  启动 FastAPI 服务，并固定监听 `3000`
- `npm run e2e`
  运行默认 E2E 测试
- `npm run e2e:headed`
  用可视浏览器运行，便于观察实际操作
- `npm run e2e:ui`
  使用 Playwright UI 模式调试
- `npm run e2e:install`
  下载浏览器内核

## Playwright 配置思路

[`playwright.config.js`](/Users/cx/cx/obsidian_search/playwright.config.js) 的关键点：

- `testDir` 指向 `tests/e2e`
- `baseURL` 默认是 `http://127.0.0.1:3000`
- `webServer.command` 使用 `npm run start:web`
- `webServer.url` 指向 `baseURL`
- `reuseExistingServer: true`
- 失败时保留：
  - `trace`
  - `screenshot`
  - `video`

这意味着测试启动时会自动拉起本地服务，不需要先手工开服务。

## E2E 用例做了什么

[`tests/e2e/smoke.spec.js`](/Users/cx/cx/obsidian_search/tests/e2e/smoke.spec.js) 当前实现的是一个基础 smoke test：

1. 打开首页 `/`
2. 监听并收集：
   - `console`
   - `pageerror`
   - `requestfailed`
   - `4xx/5xx response`
3. 如果页面存在登录按钮，则点击登录按钮
4. 如果没有登录按钮，则回退点击受保护按钮 `增量同步`
5. 输出调试产物到测试结果目录
6. 对异常做断言

这是为了兼容当前项目页面的实际情况：

- 当前页面没有单独的“登录按钮”
- 页面上只有 `x-api-token` 输入框和受保护操作按钮

所以这里把“登录类验证”抽象成了“鉴权相关交互验证”。

## Token 场景怎么跑

如果后端启用了 `api_token` 校验，可以这样传入：

```bash
OBS_E2E_API_TOKEN=your-token npm run e2e
```

测试会自动把这个值填进页面里的 `#apiToken` 输入框。

## 日常运行方式

最常用的是：

```bash
npm run e2e
```

如果想看到浏览器窗口：

```bash
npm run e2e:headed
```

如果要调试步骤、定位具体行为：

```bash
npm run e2e:ui
```

## 结果产物在哪里

运行后常见产物包括：

- `playwright-report/`
- `test-results/`

本次验证里生成了：

- [`playwright-report/index.html`](/Users/cx/cx/obsidian_search/playwright-report/index.html)
- `test-results/.../console-messages.json`
- `test-results/.../page-errors.json`
- `test-results/.../failed-requests.json`
- `test-results/.../response-issues.json`

如果测试失败，这些文件是第一优先级的排查入口。

## 本次实际验证结果

这套环境已经在当前机器上真实跑通：

```bash
npm run e2e
```

结果是：

- 本地服务成功启动在 `127.0.0.1:3000`
- Playwright 成功打开页面
- 测试通过，`1 passed`

## 常见问题

### 1. 浏览器没装好

现象：

- 运行 `npm run e2e` 时提示缺少浏览器

解决：

```bash
npm run e2e:install
```

### 2. 3000 端口无法绑定

现象：

- 报错类似 `operation not permitted`
- 或者 `address already in use`

可能原因：

- 当前环境有沙箱限制
- 3000 端口已被其他进程占用

解决建议：

1. 先检查端口占用

```bash
lsof -i :3000
```

2. 如有需要，先停止占用进程，或调整 `PLAYWRIGHT_BASE_PORT`

3. 如果是在受限沙箱环境中运行，可能需要提升权限后再启动本地服务

### 3. 后端依赖未准备好

现象：

- `scripts/start.sh` 启动失败
- `uvicorn` 不存在
- Python 包缺失

解决：

先确保 Python 环境可用。当前脚本会优先使用项目下的 `.venv`。

如有需要，可先手动准备：

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### 4. 页面没有真正的登录按钮

这不是环境问题，而是当前项目 UI 本身的结构。

当前测试已经兼容：

- 优先点“登录”
- 没有登录按钮时，改点受保护操作按钮验证鉴权链路

## 迁移到其他机器的最短流程

如果你只想在另一台机器上尽快跑起来，照这个顺序执行：

```bash
git clone <repo>
cd obsidian_search
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
npm install -D @playwright/test
npm run e2e:install
npm run e2e
```

如果后端要求 token：

```bash
OBS_E2E_API_TOKEN=your-token npm run e2e
```

## 后续可扩展方向

这套环境目前是最小可用版，后面可以继续加：

- 自动截图关键步骤
- 失败时导出 HAR
- 针对特定按钮的专项用例
- 更像 OpenCloud 的步骤化断言
- 登录成功后页面状态校验
- 对 console warning 做分级过滤

如果后面要复用到更多项目，建议把这套模式抽象成统一模板：

- 一个固定的 `playwright.config`
- 一个基础 `smoke` 用例
- 一个通用的浏览器日志采集器
- 一份项目级运行说明
