"""
Run the GitLab AI Chatbot backend.

Usage:
    python run.py              # default: host=0.0.0.0, port=8000
    python run.py --port 8080
    python run.py --reload     # enable auto-reload on file changes (dev mode)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the GitLab AI Chatbot backend")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev mode)")
    args = parser.parse_args()

    # Make sure we can import app from the backend directory
    env = os.environ.copy()
    pythonpath = str(BACKEND)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pythonpath}:{existing}" if existing else pythonpath

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]
    if args.reload:
        cmd.append("--reload")

    print(f"Starting backend on http://{args.host}:{args.port}")
    print(f"Working directory: {BACKEND}")
    if args.reload:
        print("Auto-reload enabled (dev mode)")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(cmd, cwd=str(BACKEND), env=env, check=True)
    except KeyboardInterrupt:
        print("\nBackend stopped.")
    except subprocess.CalledProcessError as e:
        print(f"\nBackend exited with code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("uvicorn not found. Install dependencies with:", file=sys.stderr)
        print(f"  pip install -r {BACKEND / 'requirements.txt'}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
