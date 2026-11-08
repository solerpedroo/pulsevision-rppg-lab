import fcntl
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import Settings
from .schemas import Job

IDENTIFIER = re.compile(r"^[0-9a-f]{32}$")


class JobManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.files = self.root / "jobs"
        self.files.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.guard = (self.root / "daemon.lock").open("a")
        try:
            fcntl.flock(self.guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.guard.close()
            raise RuntimeError("Storage already owned by another API process") from None
        self.db = sqlite3.connect(self.root / "jobs.sqlite", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, status TEXT, method TEXT, roi TEXT, progress REAL,
            created_at REAL, updated_at REAL, expires_at REAL, error TEXT)""")
        self.db.commit()
        self.lock = threading.RLock()
        self.rate_lock = threading.Lock()
        self.rates: dict[str, deque[float]] = defaultdict(deque)
        self.uploads = 0
        self.active: tuple[str, subprocess.Popen[bytes], float] | None = None
        self.stop_event = threading.Event()
        for item in self.all():
            if item.status in {"queued", "processing"}:
                self.clear_files(item.id)
                self.update(item.id, status="failed", error="service_interrupted")
        for path in self.files.iterdir():
            if IDENTIFIER.fullmatch(path.name) and path.name not in {
                item.id for item in self.all()
            }:
                self.clear_files(path.name)
        self.cleanup()
        self.thread = threading.Thread(target=self._loop, daemon=True, name="video-job-supervisor")

    def start(self) -> None:
        self.thread.start()

    def directory(self, identifier: str) -> Path:
        if not IDENTIFIER.fullmatch(identifier):
            raise KeyError(identifier)
        return self.files / identifier

    def all(self) -> list[Job]:
        with getattr(self, "lock", threading.RLock()):
            rows = self.db.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
        names = [
            "id",
            "status",
            "method",
            "roi",
            "progress",
            "created_at",
            "updated_at",
            "expires_at",
            "error",
        ]
        return [Job(**dict(zip(names, row, strict=True))) for row in rows]

    def get(self, identifier: str) -> Job:
        self.directory(identifier)
        with self.lock:
            row = self.db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise KeyError(identifier)
        names = [
            "id",
            "status",
            "method",
            "roi",
            "progress",
            "created_at",
            "updated_at",
            "expires_at",
            "error",
        ]
        return Job(**dict(zip(names, row, strict=True)))

    def update(self, identifier: str, **changes: Any) -> None:
        if not set(changes).issubset({"status", "progress", "error", "expires_at"}):
            raise ValueError("Invalid state fields")
        changes["updated_at"] = time.time()
        with self.lock:
            self.db.execute(
                "UPDATE jobs SET " + ",".join(name + "=?" for name in changes) + " WHERE id=?",
                (*changes.values(), identifier),
            )
            self.db.commit()

    def reserve(self) -> bool:
        with self.lock:
            pending = sum(x.status in {"queued", "processing"} for x in self.all())
            if pending + self.uploads >= self.settings.max_pending:
                return False
            self.uploads += 1
            return True

    def release(self) -> None:
        with self.lock:
            self.uploads -= 1

    def enqueue(self, identifier: str, method: str, roi: str, container: str) -> Job:
        now = time.time()
        options = asdict(self.settings)
        options.update(
            model=str(self.settings.model.resolve()),
            root=str(self.root),
            method=method,
            roi=roi,
            container=container,
        )
        options.pop("api_key")
        (self.directory(identifier) / "options.json").write_text(json.dumps(options))
        with self.lock:
            self.db.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    identifier,
                    "queued",
                    method,
                    roi,
                    0,
                    now,
                    now,
                    now + self.settings.retention_s,
                    None,
                ),
            )
            self.db.commit()
        return self.get(identifier)

    def allow(self, peer: str, *, upload: bool) -> bool:
        with self.rate_lock:
            now = time.monotonic()
            if len(self.rates) > 2048:
                self.rates = defaultdict(
                    deque,
                    {
                        key: value
                        for key, value in self.rates.items()
                        if value and value[-1] > now - 60
                    },
                )
            key = peer + (":upload" if upload else ":request")
            queue = self.rates[key]
            while queue and queue[0] <= now - 60:
                queue.popleft()
            limit = (
                self.settings.upload_limit_per_minute
                if upload
                else self.settings.request_limit_per_minute
            )
            if len(queue) >= limit:
                return False
            queue.append(now)
            return True

    def clear_files(self, identifier: str) -> None:
        directory = self.directory(identifier)
        if directory.is_symlink():
            directory.unlink()
        else:
            shutil.rmtree(directory, ignore_errors=True)

    def _stop_active(self, identifier: str) -> None:
        if self.active is None or self.active[0] != identifier:
            return
        process = self.active[1]
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        self.active = None

    def cancel(self, identifier: str, *, delete: bool = False) -> Job | None:
        with self.lock:
            item = self.get(identifier)
            if not delete and item.status not in {"queued", "processing"}:
                if item.status == "cancelled":
                    return item
                raise ValueError("job_not_active")
            self._stop_active(identifier)
            self.clear_files(identifier)
            if delete:
                self.db.execute("DELETE FROM jobs WHERE id=?", (identifier,))
                self.db.commit()
                return None
            if item.status == "expired":
                return item
            self.update(
                identifier,
                status="cancelled",
                error="cancelled_by_user",
                expires_at=time.time() + self.settings.retention_s,
            )
            return self.get(identifier)

    def cleanup(self) -> None:
        with self.lock:
            now = time.time()
            known = {item.id for item in self.all()}
            for item in self.all():
                if item.expires_at <= now and item.status != "expired":
                    self._stop_active(item.id)
                    self.clear_files(item.id)
                    self.update(item.id, status="expired", error="retention_expired")
                elif (
                    item.status == "expired" and item.expires_at + self.settings.retention_s <= now
                ):
                    self.db.execute("DELETE FROM jobs WHERE id=?", (item.id,))
            self.db.commit()
            for path in self.files.iterdir():
                if IDENTIFIER.fullmatch(path.name) and path.name not in known:
                    if path.stat().st_mtime <= now - self.settings.retention_s:
                        self.clear_files(path.name)

    def _loop(self) -> None:
        last_cleanup = 0.0
        while not self.stop_event.wait(0.05):
            with self.lock:
                try:
                    if self.active:
                        identifier, process, started = self.active
                        directory = self.directory(identifier)
                        timed_out = time.monotonic() - started > self.settings.job_timeout_s
                        oversized = (
                            sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
                            > self.settings.max_job_bytes
                        )
                        if timed_out or oversized:
                            self._stop_active(identifier)
                            self.clear_files(identifier)
                            self.update(
                                identifier,
                                status="failed",
                                error="job_timeout" if timed_out else "storage_limit",
                            )
                        elif process.poll() is not None:
                            try:
                                result = json.loads((directory / "done.json").read_text())
                            except (OSError, ValueError):
                                result = {"ok": False, "error": "worker_terminated"}
                            success = process.returncode == 0 and result.get("ok") is True
                            (directory / "input.bin").unlink(missing_ok=True)
                            if not success:
                                self.clear_files(identifier)
                            self.update(
                                identifier,
                                status="completed" if success else "failed",
                                progress=1 if success else self.get(identifier).progress,
                                error=None if success else result.get("error", "processing_failed"),
                                expires_at=time.time() + self.settings.retention_s,
                            )
                            self.active = None
                        else:
                            try:
                                progress = json.loads((directory / "progress.json").read_text())[
                                    "progress"
                                ]
                                self.update(identifier, progress=min(0.99, max(0, float(progress))))
                            except (OSError, ValueError, KeyError):
                                pass
                    if self.active is None:
                        queued = next((x for x in self.all() if x.status == "queued"), None)
                        if queued:
                            environment = {
                                **{
                                    key: value
                                    for key, value in os.environ.items()
                                    if key
                                    in {
                                        "PATH",
                                        "HOME",
                                        "LANG",
                                        "LC_ALL",
                                        "VIRTUAL_ENV",
                                        "PYTHONPATH",
                                        "LD_LIBRARY_PATH",
                                    }
                                },
                                "OPENBLAS_NUM_THREADS": "1",
                                "OMP_NUM_THREADS": "1",
                                "MPLBACKEND": "Agg",
                            }
                            try:
                                process = subprocess.Popen(
                                    [
                                        sys.executable,
                                        "-m",
                                        "services.api.app.worker",
                                        str(self.directory(queued.id)),
                                        str(os.getpid()),
                                    ],
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    env=environment,
                                )
                            except OSError:
                                self.clear_files(queued.id)
                                self.update(queued.id, status="failed", error="worker_start_failed")
                                continue
                            self.active = queued.id, process, time.monotonic()
                            self.update(queued.id, status="processing")
                    if time.monotonic() - last_cleanup > self.settings.cleanup_interval_s:
                        self.cleanup()
                        last_cleanup = time.monotonic()
                except (OSError, ValueError, KeyError):
                    if self.active:
                        identifier = self.active[0]
                        self._stop_active(identifier)
                        self.clear_files(identifier)
                        self.update(identifier, status="failed", error="supervisor_error")

    def close(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=5)
        with self.lock:
            for item in self.all():
                if item.status in {"queued", "processing"}:
                    self.cancel(item.id)
            self.db.close()
            fcntl.flock(self.guard, fcntl.LOCK_UN)
            self.guard.close()
