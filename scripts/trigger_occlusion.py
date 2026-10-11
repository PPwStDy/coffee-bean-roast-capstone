"""Send a synthetic solid-color frame to demonstrate the occlusion rejection."""

from __future__ import annotations

import argparse
import io
import json
import urllib.error
import urllib.request

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080/predict")
    parser.add_argument("--color", choices=("white", "black"), default="white")
    args = parser.parse_args()

    color = (255, 255, 255) if args.color == "white" else (0, 0, 0)
    buffer = io.BytesIO()
    Image.new("RGB", (224, 224), color=color).save(buffer, format="PNG")
    request = urllib.request.Request(
        args.url,
        data=buffer.getvalue(),
        headers={"Content-Type": "image/png"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            print(f"Unexpected HTTP {response.status}: {response.read().decode()}")
            return 1
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read())
        if exc.code != 422:
            print(f"Expected HTTP 422, received HTTP {exc.code}: {body}")
            return 1
        print(f"Occlusion guard rejected the synthetic frame (HTTP 422): {body['detail']['error']}")
        return 0
    except urllib.error.URLError as exc:
        print(f"Could not reach API at {args.url}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
