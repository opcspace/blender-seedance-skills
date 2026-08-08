#!/usr/bin/env python3
"""Submit and poll a Volcengine Ark video-generation task.

The model name is deliberately supplied by VOLCENGINE_SEEDANCE_MODEL because
model IDs and availability are account/region/version dependent.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"


def request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Volcengine HTTP {exc.code}: {detail[:2000]}") from exc


def submit(args: argparse.Namespace, token: str, model: str) -> str:
    text = args.prompt.strip()
    if args.ratio:
        text += f" --ratio {args.ratio}"
    if args.duration:
        text += f" --dur {args.duration}"
    content = [{"type": "text", "text": text}]
    content.extend({"type": "image_url", "image_url": {"url": url}} for url in args.image_url)
    result = request("POST", BASE_URL, token, {"model": model, "content": content, "return_last_frame": args.return_last_frame})
    task_id = result.get("id") or result.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"No task ID returned: {json.dumps(result, ensure_ascii=False)}")
    return task_id


def poll(task_id: str, token: str, timeout: int, interval: int) -> dict:
    query = urllib.parse.urlencode({"filter.task_ids": task_id})
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = request("GET", f"{BASE_URL}?{query}", token)
        items = result.get("items") or result.get("data", {}).get("items") or []
        task = items[0] if items else result.get("data", {})
        status = task.get("status", "unknown")
        print(f"status={status}", flush=True)
        if status in {"succeeded", "failed", "cancelled", "expired"}:
            return task
        time.sleep(interval)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--image-url", action="append", default=[], help="Public HTTPS reference image URL; repeatable")
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--return-last-frame", action="store_true")
    parser.add_argument("--output-json", type=pathlib.Path)
    args = parser.parse_args()
    token = os.environ.get("VOLCENGINE_API_KEY") or os.environ.get("ARK_API_KEY")
    model = os.environ.get("VOLCENGINE_SEEDANCE_MODEL")
    if not token:
        parser.error("Set VOLCENGINE_API_KEY or ARK_API_KEY")
    if not model:
        parser.error("Set VOLCENGINE_SEEDANCE_MODEL to a model ID or Ark endpoint ID")
    task_id = submit(args, token, model)
    print(f"task_id={task_id}", flush=True)
    result = poll(task_id, token, args.timeout, args.interval)
    output = {"task_id": task_id, "model": model, "result": result}
    if args.output_json:
        args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
