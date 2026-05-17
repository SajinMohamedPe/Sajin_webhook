# GitHub Webhook Receiver & PR Review Bot

Flask server that receives GitHub webhooks and verifies HMAC-SHA256 signatures. Paired with a GitHub Actions workflow that posts an AI-generated PR review (via Gemini) as a formal GitHub review with inline diff annotations.

## Project Structure

- `webhook_receiver.py` — Flask webhook server
- `.github/workflows/pr-review.yml` — Gemini PR review workflow
- `test-webhook.txt` — local test file

## Webhook Server

### Handled events

| Event | What it logs |
|---|---|
| `ping` | Hook ID and GitHub zen message |
| `push` | Pusher, branch, commit count |
| `pull_request` | PR title, author, action |
| `issues` | Issue title, action |
| `issue_comment` | Commenter, issue number, comment preview; dispatches slash commands |

### Slash commands (via `issue_comment`)

Post a comment on any issue or PR starting with `/` to trigger a command:

| Command | Effect |
|---|---|
| `/ping <target>` | Logs a ping request for the target |
| `/help` | Logs available commands |

## Setup

### 1) Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip flask
```

### 2) Set webhook secret

Use the same value here and in GitHub webhook settings.

```bash
export WEBHOOK_SECRET="replace-with-your-secret"
```

### 3) Run the server

```bash
python webhook_receiver.py
```

Server starts on `http://127.0.0.1:5000`. Health check:

```bash
curl -i http://127.0.0.1:5000/health
```

### 4) Expose localhost with ngrok

```bash
ngrok http 127.0.0.1:5000
```

Your webhook endpoint: `https://<your-ngrok-domain>/webhook`

### 5) Configure GitHub webhook

**Settings → Webhooks → Add webhook**

- **Payload URL**: `https://<your-ngrok-domain>/webhook`
- **Content type**: `application/json`
- **Secret**: same value as `WEBHOOK_SECRET`
- **Events**: select `push`, `pull_request`, `issues`, `issue_comments`

Use **Recent Deliveries** to inspect payloads and responses.

### 6) Test locally without GitHub

```bash
export PAYLOAD='{"zen":"Keep it logically awesome.","hook_id":12345}'
SIG=$(python3 -c 'import os,hmac,hashlib; p=os.environ["PAYLOAD"].encode(); s=os.environ["WEBHOOK_SECRET"].encode(); print("sha256="+hmac.new(s,p,hashlib.sha256).hexdigest())')
curl -i -X POST "http://127.0.0.1:5000/webhook" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -H "X-GitHub-Delivery: local-test-1" \
  -H "X-Hub-Signature-256: $SIG" \
  --data "$PAYLOAD"
```

Expected response:

```json
{"status":"ok","delivery_id":"local-test-1","event":"ping"}
```

## Gemini PR Review Action

`.github/workflows/pr-review.yml` triggers on every PR open, update, or reopen. It fetches the diff, sends it to Gemini, and posts the result as a **formal GitHub review** (visible under the Reviews section) with **inline comments** on specific diff lines.

### What it posts

- A review with sections: Summary, Risks, Security Vulnerabilities, Suggested Tests, Optional Improvements
- Up to 5 inline comments attached to changed lines in the diff
- Metadata: model used, files reviewed, diff size, inline comment count

### Configure

**Settings → Secrets and variables → Actions**

- **Secret**: `GEMINI_API_KEY`
- **Variable**: `GEMINI_MODEL` (e.g. `gemini-2.5-flash`)

### Trigger

1. Push a branch and open a PR
2. Check the **Actions** tab for the run log
3. Check the PR **Reviews** section and **Files changed** tab for inline annotations

### Limits

- Max 25 files, 14,000 patch characters per review (cost/safety cap)
- Inline comments only on changed lines; invalid line references are dropped
- If `GEMINI_API_KEY` or `GEMINI_MODEL` is missing, a skip message is posted instead of failing silently

## Troubleshooting

- **`401 Invalid signature`** — `WEBHOOK_SECRET` mismatch, or Flask started before the variable was exported. Restart Flask after exporting.
- **`400 Invalid JSON`** — missing `Content-Type: application/json` header.
- **ngrok URL changed** — update the Payload URL in GitHub webhook settings.
- **Workflow posts raw JSON** — Gemini response was truncated; increase `maxOutputTokens` in the workflow or reduce diff size.
- **Inline comments: 0** — Gemini didn't reference valid changed lines, or JSON parse failed (check workflow logs for the warning).

## Stop / Cleanup 

```bash
# Stop Flask or ngrok
Ctrl + C

# Deactivate virtualenv
deactivate
```
