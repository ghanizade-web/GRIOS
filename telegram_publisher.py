from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://api.telegram.org"
RTL_MARK = "\u2067"
POP_DIRECTIONAL_ISOLATE = "\u2069"


def chunk_message(message: str, limit: int = 4000) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be positive")
    text = message.strip()
    if not text:
        raise ValueError("message is empty")
    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = line if not current else current + "\n" + line
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current = line
    if current:
        chunks.append(current)
    return chunks


def apply_rtl_direction(message: str) -> str:
    """Isolate Persian-containing lines so mixed RTL/LTR text renders predictably."""
    rendered = []
    for line in message.splitlines():
        if any("\u0600" <= char <= "\u06ff" for char in line):
            rendered.append(f"{RTL_MARK}{line}{POP_DIRECTIONAL_ISOLATE}")
        else:
            rendered.append(line)
    return "\n".join(rendered)


def _send(token: str, chat_id: str, text: str, timeout: int = 20) -> None:
    body = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }).encode("utf-8")
    request = urllib.request.Request(
        API_ROOT + "/bot" + token + "/sendMessage",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                if response.status != 200 or not result.get("ok"):
                    raise RuntimeError("TELEGRAM_API_REJECTED")
                return
        except urllib.error.HTTPError as exc:
            if (exc.code == 429 or 500 <= exc.code < 600) and attempt < 2:
                delay = 1
                try:
                    details = json.loads(exc.read().decode("utf-8"))
                    delay = int(details.get("parameters", {}).get("retry_after", 1))
                except (ValueError, TypeError, AttributeError):
                    pass
                time.sleep(max(1, min(delay, 30)))
                continue
            raise RuntimeError(f"TELEGRAM_HTTP_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt < 2:
                time.sleep(1)
                continue
            raise RuntimeError("TELEGRAM_NETWORK_ERROR") from None
        except (ValueError, TypeError):
            raise RuntimeError("TELEGRAM_INVALID_RESPONSE") from None
    raise RuntimeError("TELEGRAM_DELIVERY_FAILED")


def publish_report(report_path: str | Path, token: str, chat_id: str) -> int:
    report = Path(report_path).read_text(encoding="utf-8")
    chunks = chunk_message(report)
    for chunk in chunks:
        _send(token, chat_id, apply_rtl_direction(chunk))
    return len(chunks)


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    report_path = Path(os.getenv("GRIOS_REPORT_PATH", "reports/latest.txt"))

    if not token and not chat_id:
        print("TELEGRAM_PUBLISH: SKIPPED_NOT_CONFIGURED")
        return 0
    if not token or not chat_id:
        print("TELEGRAM_PUBLISH: CONFIGURATION_INCOMPLETE")
        return 2
    if not report_path.is_file():
        print("TELEGRAM_PUBLISH: REPORT_NOT_FOUND")
        return 2
    try:
        count = publish_report(report_path, token, chat_id)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"TELEGRAM_PUBLISH: FAILED ({exc})")
        return 1
    print(f"TELEGRAM_PUBLISH: SENT ({count} message(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
