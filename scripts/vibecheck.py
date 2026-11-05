import subprocess
import time
import os
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "backend"))
    from app import commerce

    db_path = root / "orders.sqlite3"
    drafts = [r for r in commerce.list_records(db_path, "local-shop") if r.get("status") == "draft" and r.get("items")]
    if not drafts:
        subprocess.run([sys.executable, str(root / "scripts" / "seed_demo.py"), "--no-reset"], check=True)
        drafts = [r for r in commerce.list_records(db_path, "local-shop") if r.get("status") == "draft" and r.get("items")]

    buyer_path = commerce.create_link(db_path, "local-shop", drafts[0]["reference"], 72)["buyer_path"]
    print(f"[+] Active buyer path: {buyer_path}")

    env = {
        **os.environ,
        "PYTHONPATH": "backend",
        "SELLER_API_KEYS": '{"demo-seller-key":"local-shop"}',
        "PROVIDER": "deterministic",
        "MODEL": "deterministic"
    }

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8799"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)

    chrome = subprocess.Popen([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
        "--remote-debugging-port=9333",
        "about:blank"
    ])
    time.sleep(2.5)

    try:
        subprocess.run(["node", str(root / "scripts" / "vibecheck_runner.js"), buyer_path], check=True)
    finally:
        chrome.terminate()
        chrome.wait()
        server.terminate()
        server.wait()

if __name__ == "__main__":
    main()
