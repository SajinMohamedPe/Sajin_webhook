import hashlib
import hmac
import json
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify that the request came from GitHub."""
    if not WEBHOOK_SECRET:
        return False
    if not signature_header:
        return False
    # BUG FIX: original code used `hmac.new(...)` — the correct Python call is
    # `hmac.new(key, msg, digestmod)`. The function exists, but the original
    # had a typo: `hmac.new` should match the module's actual function name.
    # More critically: use hmac.new() not hmac.HMAC() directly, and always
    # use hmac.compare_digest() (not ==) to prevent timing attacks.
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


ALLOWED_COMMANDS = ["/ping", "/help"]

def handle_slash_command(command: str, args: list, issue_number: int, user: str):
    if command == "/ping":
        target = args[0]
        print(f"Pinging {target} on #{issue_number} requested by {user}")

    elif command == "/help":
        print(f"Help requested on #{issue_number} by {user}")
        print(f"Available commands: {', '.join(ALLOWED_COMMANDS)}")

    else:
        print(f"Unknown command '{command}' from {user} on #{issue_number}")


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    delivery_id = request.headers.get("X-GitHub-Delivery", "unknown")
    event = request.headers.get("X-GitHub-Event", "unknown")

    # 1. Verify signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.data, signature):
        return jsonify(
            {
                "error": "Invalid signature",
                "delivery_id": delivery_id,
                "event": event,
            }
        ), 401

    # 2. Parse the event type
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(
            {
                "error": "Invalid or missing JSON payload",
                "delivery_id": delivery_id,
                "event": event,
            }
        ), 400

    print(f"\n--- Delivery: {delivery_id} | Event: {event} ---")

    # 3. Handle specific events
    if event == "ping":
        zen = payload.get("zen", "")
        hook_id = payload.get("hook_id", "")
        print(f"Ping received! Hook ID: {hook_id}")
        print(f"GitHub zen: '{zen}'")
        print("Webhook registered successfully.")

    elif event == "push":
        branch = payload.get("ref", "").replace("refs/heads/", "")
        pusher = payload.get("pusher", {}).get("name", "unknown")
        commits = len(payload.get("commits", []))
        print(f"{pusher} pushed {commits} commit(s) to '{branch}'")

    elif event == "pull_request":
        action = payload.get("action", "unknown")  # opened, closed, synchronize, etc.
        pr_data = payload.get("pull_request", {})
        pr_title = pr_data.get("title", "unknown")
        pr_author = pr_data.get("user", {}).get("login", "unknown")
        print(f"PR '{pr_title}' by {pr_author} was {action}")

    elif event == "issues":
        action = payload.get("action", "unknown")
        issue_title = payload.get("issue", {}).get("title", "unknown")
        print(f"Issue '{issue_title}' was {action}")

    elif event == "issue_comment":
        action = payload.get("action", "unknown")
        comment_body = payload["comment"]["body"]
        commenter = payload["comment"]["user"]["login"]
        issue_number = payload["issue"]["number"]

        print(f"Comment on #{issue_number} by {commenter} ({action}): {comment_body[:80]}")

        if action == "created" and comment_body.startswith("/"):
            parts = comment_body.split()
            command = parts[0]
            args = parts[1:]
            handle_slash_command(command, args, issue_number, commenter)

    else:
        print(f"Received unhandled event: {event}")
        print(json.dumps(payload, indent=2))

    return jsonify({"status": "ok", "delivery_id": delivery_id, "event": event}), 200


if __name__ == "__main__":
    if not WEBHOOK_SECRET:
        print("WARNING: WEBHOOK_SECRET is not set. Signature verification will fail.")
    app.run(port=5000, debug=True)
