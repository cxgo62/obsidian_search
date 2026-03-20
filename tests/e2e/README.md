# Playwright E2E

This repository now includes a small Playwright setup for browser-side verification.

## Install browser

```bash
npm run e2e:install
```

## Run checks

```bash
npm run e2e
```

The test will:

- start the FastAPI UI on `http://127.0.0.1:3000`
- open the page
- capture `console`, page errors, failed requests, and `4xx/5xx` responses
- click a login button if the page has one; otherwise it clicks the auth-protected `增量同步` button

If your environment requires an API token, pass it like this:

```bash
OBS_E2E_API_TOKEN=your-token npm run e2e
```
