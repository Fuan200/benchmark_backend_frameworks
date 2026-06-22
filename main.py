import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent

WRK_THREADS = 4
WRK_CONNECTIONS = 100
WRK_DURATION = "10s"
WARMUP_DURATION = "3s"
WAIT_TIMEOUT = 15.0
OUTPUT_FILE = ROOT_DIR / "benchmark_results.json"
FRAMEWORKS_FILE = ROOT_DIR / "framework.json"


def load_frameworks() -> list[dict[str, Any]]:
    grouped_frameworks = json.loads(FRAMEWORKS_FILE.read_text(encoding="utf-8"))
    frameworks: list[dict[str, Any]] = []

    for language, entries in grouped_frameworks.items():
        for entry in entries:
            frameworks.append({"language": language, **entry})

    return frameworks


def extract(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else None


def extract_groups(pattern: str, text: str) -> tuple[str, ...] | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.groups() if match else None


def parse_wrk_output(output: str) -> dict[str, Any]:
    running = extract_groups(r"Running\s+(.+?)\s+test\s+@\s+(\S+)", output)
    config = extract_groups(r"(\d+)\s+threads and\s+(\d+)\s+connections", output)
    latency = extract_groups(r"Latency\s+(\S+)\s+(\S+)\s+(\S+)\s+([\d\.]+%)", output)
    req_sec = extract_groups(r"Req/Sec\s+(\S+)\s+(\S+)\s+(\S+)\s+([\d\.]+%)", output)
    totals = extract_groups(r"(\d+)\s+requests in\s+(.+?),\s+(\S+)\s+read", output)
    socket_errors = extract_groups(
        r"Socket errors:\s+connect\s+(\d+),\s+read\s+(\d+),\s+write\s+(\d+),\s+timeout\s+(\d+)",
        output,
    )

    return {
        "summary": {
            "test_duration": running[0] if running else None,
            "url": running[1] if running else None,
            "threads": int(config[0]) if config else None,
            "connections": int(config[1]) if config else None,
            "total_requests": int(totals[0]) if totals else None,
            "completed_in": totals[1] if totals else None,
            "total_read": totals[2] if totals else None,
            "requests_per_sec": (
                float(extract(r"Requests/sec:\s+([\d\.]+)", output))
                if extract(r"Requests/sec:\s+([\d\.]+)", output)
                else None
            ),
            "transfer_per_sec": extract(r"Transfer/sec:\s+(\S+)", output),
        },
        "latency": {
            "avg": latency[0] if latency else None,
            "stdev": latency[1] if latency else None,
            "max": latency[2] if latency else None,
            "plus_minus_stdev": latency[3] if latency else None,
        },
        "req_per_sec_per_thread": {
            "avg": req_sec[0] if req_sec else None,
            "stdev": req_sec[1] if req_sec else None,
            "max": req_sec[2] if req_sec else None,
            "plus_minus_stdev": req_sec[3] if req_sec else None,
        },
        "errors": {
            "non_2xx_3xx": (
                int(extract(r"Non-2xx or 3xx responses:\s+(\d+)", output))
                if extract(r"Non-2xx or 3xx responses:\s+(\d+)", output)
                else 0
            ),
            "socket": {
                "connect": int(socket_errors[0]) if socket_errors else 0,
                "read": int(socket_errors[1]) if socket_errors else 0,
                "write": int(socket_errors[2]) if socket_errors else 0,
                "timeout": int(socket_errors[3]) if socket_errors else 0,
            },
        },
        "raw_output": output,
    }


def ensure_dependencies() -> None:
    if shutil.which("wrk") is None:
        raise RuntimeError("`wrk` is not installed or is not available in PATH.")


def wait_for_tcp(url: str, timeout_seconds: float) -> None:
    parsed = urlparse(url)
    if not parsed.hostname or not parsed.port:
        raise ValueError(f"Invalid URL for readiness check: {url}")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=1):
                return
        except OSError:
            time.sleep(0.25)

    raise TimeoutError(f"Timed out waiting for {parsed.hostname}:{parsed.port}")


def build_wrk_command(url: str, threads: int, connections: int, duration: str) -> list[str]:
    return ["wrk", f"-t{threads}", f"-c{connections}", f"-d{duration}", url]


def run_wrk(url: str, threads: int, connections: int, duration: str) -> dict[str, Any]:
    command = build_wrk_command(url, threads, connections, duration)
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "wrk failed")

    result = parse_wrk_output(completed.stdout)
    result["wrk_command"] = " ".join(shlex.quote(part) for part in command)
    return result


def start_server(
    command: str,
    cwd: Path,
) -> tuple[subprocess.Popen[str], Any, Any]:
    stdout_log = tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", delete=False)
    stderr_log = tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", delete=False)

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        shell=True,
        stdout=stdout_log,
        stderr=stderr_log,
        text=True,
    )
    return process, stdout_log, stderr_log


def stop_server(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def read_logs(stdout_log: Any, stderr_log: Any) -> tuple[str, str]:
    stdout_log.flush()
    stderr_log.flush()
    stdout_log.seek(0)
    stderr_log.seek(0)
    return stdout_log.read(), stderr_log.read()


def cleanup_logs(stdout_log: Any, stderr_log: Any) -> None:
    stdout_name = stdout_log.name
    stderr_name = stderr_log.name
    stdout_log.close()
    stderr_log.close()
    for path in (stdout_name, stderr_name):
        try:
            os.unlink(path)
        except OSError:
            pass


def benchmark_framework(framework: dict[str, Any]) -> dict[str, Any]:
    cwd = ROOT_DIR / framework["cwd"]

    process, stdout_log, stderr_log = start_server(framework["run"], cwd)
    started_at = time.time()

    try:
        wait_for_tcp(framework["url"], WAIT_TIMEOUT)

        if WARMUP_DURATION:
            run_wrk(
                framework["url"],
                min(WRK_THREADS, 2),
                min(WRK_CONNECTIONS, 50),
                WARMUP_DURATION,
            )

        result = run_wrk(framework["url"], WRK_THREADS, WRK_CONNECTIONS, WRK_DURATION)
        result["name"] = framework["name"]
        result["framework"] = {
            "name": framework["name"],
            "language": framework["language"],
            "cwd": framework["cwd"],
            "run": framework["run"],
            "startup_seconds": round(time.time() - started_at, 3),
        }
        return result
    except Exception as exc:
        stdout, stderr = read_logs(stdout_log, stderr_log)
        return {
            "name": framework["name"],
            "framework": {
                "name": framework["name"],
                "language": framework["language"],
                "cwd": framework["cwd"],
                "run": framework["run"],
            },
            "error": str(exc),
            "stdout": stdout,
            "stderr": stderr,
        }
    finally:
        stop_server(process)
        cleanup_logs(stdout_log, stderr_log)


def main() -> int:
    try:
        ensure_dependencies()

        payload: dict[str, Any] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "threads": WRK_THREADS,
                "connections": WRK_CONNECTIONS,
                "duration": WRK_DURATION,
                "warmup_duration": WARMUP_DURATION,
            },
            "results": [],
        }

        for framework in load_frameworks():
            payload["results"].append(benchmark_framework(framework))

        OUTPUT_FILE.write_text(json.dumps(payload, indent=2) + os.linesep, encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
