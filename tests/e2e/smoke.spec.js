const fs = require("node:fs/promises");
const { test, expect } = require("@playwright/test");

function pushConsoleMessage(store, msg) {
  const text = msg.text();
  store.push({
    type: msg.type(),
    text,
    location: msg.location(),
  });
}

function isIgnorableRequestFailure(failureText = "") {
  return /ERR_ABORTED|ERR_BLOCKED_BY_CLIENT/i.test(failureText);
}

async function writeArtifact(testInfo, name, payload) {
  const file = testInfo.outputPath(name);
  await fs.writeFile(file, JSON.stringify(payload, null, 2), "utf8");
  await testInfo.attach(name, {
    path: file,
    contentType: "application/json",
  });
}

test("collects console and network signals around auth-protected UI actions", async ({ page }, testInfo) => {
  const consoleMessages = [];
  const pageErrors = [];
  const failedRequests = [];
  const responseIssues = [];

  page.on("console", (msg) => pushConsoleMessage(consoleMessages, msg));
  page.on("pageerror", (error) => {
    pageErrors.push({
      name: error.name,
      message: error.message,
      stack: error.stack,
    });
  });
  page.on("requestfailed", (request) => {
    const failureText = request.failure()?.errorText || "unknown failure";
    if (isIgnorableRequestFailure(failureText)) return;
    failedRequests.push({
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType(),
      failureText,
    });
  });
  page.on("response", async (response) => {
    if (response.status() < 400) return;
    const request = response.request();
    responseIssues.push({
      url: response.url(),
      status: response.status(),
      method: request.method(),
      resourceType: request.resourceType(),
    });
  });

  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "Obsidian 关联检索面板" })).toBeVisible();
  await expect(page.locator("#statsPanel")).toContainText("目标目录");

  const token = process.env.OBS_E2E_API_TOKEN;
  if (token) {
    await page.locator("#apiToken").fill(token);
  }

  const loginButton = page.getByRole("button", { name: /^(登录|log in|login|sign in)$/i });
  if (await loginButton.count()) {
    await loginButton.first().click();
  } else {
    await page.getByRole("button", { name: "增量同步" }).click();
  }

  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);

  await writeArtifact(testInfo, "console-messages.json", consoleMessages);
  await writeArtifact(testInfo, "page-errors.json", pageErrors);
  await writeArtifact(testInfo, "failed-requests.json", failedRequests);
  await writeArtifact(testInfo, "response-issues.json", responseIssues);

  const severeConsole = consoleMessages.filter((entry) => ["error", "warning", "assert"].includes(entry.type));
  const unexpectedResponses = responseIssues.filter((entry) => {
    if (entry.status === 401 && !token) {
      return false;
    }
    return true;
  });

  expect.soft(pageErrors, `Unhandled page errors: ${JSON.stringify(pageErrors, null, 2)}`).toEqual([]);
  expect.soft(failedRequests, `Failed requests: ${JSON.stringify(failedRequests, null, 2)}`).toEqual([]);
  expect.soft(
    severeConsole,
    `Console warnings/errors: ${JSON.stringify(severeConsole, null, 2)}`,
  ).toEqual([]);
  expect(
    unexpectedResponses,
    `Unexpected HTTP responses: ${JSON.stringify(unexpectedResponses, null, 2)}`,
  ).toEqual([]);
});
