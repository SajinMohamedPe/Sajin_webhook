# GitHub Webhook Receiver (Flask)

Small Flask server that receives GitHub webhooks, verifies the HMAC SHA-256 signature, and logs common events (`ping`, `push`, `pull_request`, `issues`).

## Project Structure

- `../webhook_receiver.py` - webhook server
- `test-webhook.txt` - local test file

## Prerequisites

- Python 3.9+
- `pip`
- [ngrok](https://ngrok.com/) (for receiving GitHub webhooks on localhost)

## 1) Setup

From the git project folder:

```bash
cd "/Users/Sajin/Downloads/Github/webhook-learning/Sajin_webhook"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install flask
```

## 2) Set Webhook Secret

Use the same value in both your terminal and GitHub webhook settings.
Important: set this in the same terminal session where you start Flask.

```bash
export WEBHOOK_SECRET="replace-with-your-secret"
```

Optional check:

```bash
echo "$WEBHOOK_SECRET"
```

## 3) Run the Server

```bash
python ../webhook_receiver.py
```

If you change `WEBHOOK_SECRET`, stop and restart the Flask server so it picks up the new value.

Server starts on `http://127.0.0.1:5000`.

Health check:

```bash
curl -i http://127.0.0.1:5000/health
```

## 4) Expose Localhost with ngrok

In a new terminal:

```bash
ngrok http 5000
```

Copy the HTTPS forwarding URL from ngrok, for example:

`https://abcd-1234.ngrok-free.app`

Your webhook endpoint becomes:

`https://abcd-1234.ngrok-free.app/webhook`

## 5) Configure GitHub Webhook

In your repository:

1. Go to **Settings -> Webhooks -> Add webhook**
2. **Payload URL**: `https://<your-ngrok-domain>/webhook`
3. **Content type**: `application/json`
4. **Secret**: same value as `WEBHOOK_SECRET`
5. Select events:
   - Just the push event, or
   - Let me select individual events (`push`, `pull_request`, `issues`, etc.)
6. Click **Add webhook**

Use **Recent Deliveries** in GitHub webhook settings to inspect request/response status.

## 6) Test Locally with a Signed Request (No GitHub Needed)

Generate a valid `X-Hub-Signature-256` and POST it:

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

If signature and JSON are valid, you should get HTTP `200` with:

```json
{"status":"ok","delivery_id":"local-test-1","event":"ping"}
```

## 7) Trigger Real GitHub Events

After webhook setup, trigger events in your repository:

```bash
# push event
git add .
git commit -m "test webhook"
git push
```

Also try opening/updating a pull request and creating/updating an issue.

## 8) Gemini PR Review Action

This repository includes `.github/workflows/pr-review.yml`, which runs on pull request events and posts an AI-generated review summary.

### Configure required GitHub settings

In your repository, go to **Settings -> Secrets and variables -> Actions** and add:

- **Secret**: `GEMINI_API_KEY`
- **Variable**: `GEMINI_MODEL` (example: `gemini-1.5-flash`)

The model is read from `GEMINI_MODEL` at runtime (it is not hardcoded in the workflow).

### Trigger the workflow

1. Push a branch with changes
2. Open a PR (or update an existing PR)
3. Check:
   - **Actions** tab for workflow logs
   - PR conversation for `AI PR Review (Gemini)` comment

### Notes

- The workflow reviews only a bounded portion of the diff for safety/cost control.
- If `GEMINI_API_KEY` or `GEMINI_MODEL` is missing, the workflow posts a skip message instead of failing silently.

## Troubleshooting

- `401 Invalid signature`
  - `WEBHOOK_SECRET` in terminal does not match GitHub webhook secret.
  - Flask was started before `WEBHOOK_SECRET` was exported.
  - After changing `WEBHOOK_SECRET`, restart Flask (`Ctrl + C`, then run again).
- `400 Invalid or missing JSON payload`
  - Request body is not valid JSON or missing `Content-Type: application/json`.
- ngrok URL changed
  - Update GitHub webhook payload URL with the new ngrok URL.
- Server warning: `WEBHOOK_SECRET is not set`
  - Export the variable before running the server.
- Workflow comment says `GEMINI_API_KEY` missing
  - Add `GEMINI_API_KEY` under **Settings -> Secrets and variables -> Actions -> Secrets**.
- Workflow comment says `GEMINI_MODEL` missing
  - Add `GEMINI_MODEL` under **Settings -> Secrets and variables -> Actions -> Variables**.

## Stop / Cleanup

Stop running services with `Ctrl + C`.

Deactivate virtual environment:

```bash
deactivate
```
