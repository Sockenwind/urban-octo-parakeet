"""Hintergrundarbeit: Tasks für Vorschau/Analyse und eine Export-Warteschlange."""
from __future__ import annotations

import traceback
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from ..ffmpeg_tools import CancelToken, Cancelled
from ..pipeline import run_job

CANCELLED = "__cancelled__"

_pools: dict = {}


def pool(name: str) -> QThreadPool:
    """'preview' (mehrere parallel) und 'export' (immer nur einer)."""
    if name not in _pools:
        p = QThreadPool()
        p.setMaxThreadCount(1 if name == "export" else 3)
        _pools[name] = p
    return _pools[name]


class TaskSignals(QObject):
    done = Signal(object)
    failed = Signal(str, str)
    progress = Signal(float, str)


class Task(QRunnable):
    """Führt fn(*args, **kwargs) im Hintergrund aus; Ergebnis/Fehler kommen als Signale im GUI-Thread an."""

    _alive: set = set()

    def __init__(self, fn: Callable, *args, progress: bool = False, cancellable: bool = False, **kwargs):
        super().__init__()
        self.setAutoDelete(False)
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.with_progress, self.with_cancel = progress, cancellable
        self.cancel_token = CancelToken()
        self.signals = TaskSignals()
        self.signals.done.connect(self._release)
        self.signals.failed.connect(self._release)

    def _release(self, *_args) -> None:
        Task._alive.discard(self)

    def start(self, pool_name: str = "preview") -> "Task":
        Task._alive.add(self)
        pool(pool_name).start(self)
        return self

    def cancel(self) -> None:
        self.cancel_token.cancel()

    def run(self) -> None:
        kwargs = dict(self.kwargs)
        if self.with_progress:
            kwargs["on_progress"] = self.signals.progress.emit
        if self.with_cancel:
            kwargs["cancel"] = self.cancel_token
        try:
            result = self.fn(*self.args, **kwargs)
        except Cancelled:
            self.signals.failed.emit(CANCELLED, "")
        except Exception as exc:  # noqa: BLE001 – alles an die Oberfläche melden
            log = getattr(exc, "log", "") or traceback.format_exc()
            self.signals.failed.emit(str(exc) or exc.__class__.__name__, log)
        else:
            self.signals.done.emit(result)


class ExportSignals(QObject):
    job_started = Signal(int)
    job_progress = Signal(int, float, str)
    job_done = Signal(int, str)
    job_failed = Signal(int, str, str)
    finished = Signal(int, int, bool)


class ExportRunner(QRunnable):
    """Arbeitet eine Liste von Aufträgen nacheinander ab. job_factories[i]() liefert den Job erst
    unmittelbar vor dem Start, damit Zieldateinamen eindeutig bleiben."""

    def __init__(self, ff, job_factories: list):
        super().__init__()
        self.setAutoDelete(False)
        self.ff = ff
        self.factories = job_factories
        self.cancel_token = CancelToken()
        self.signals = ExportSignals()
        self.signals.finished.connect(lambda *_: Task._alive.discard(self))

    def start(self) -> "ExportRunner":
        Task._alive.add(self)
        pool("export").start(self)
        return self

    def cancel(self) -> None:
        self.cancel_token.cancel()

    def run(self) -> None:
        ok = failed = 0
        for i, factory in enumerate(self.factories):
            if self.cancel_token.cancelled:
                break
            self.signals.job_started.emit(i)
            try:
                job = factory()
                out = run_job(self.ff, job, on_progress=lambda f, t, i=i: self.signals.job_progress.emit(i, f, t),
                              cancel=self.cancel_token)
            except Cancelled:
                break
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.signals.job_failed.emit(i, str(exc), getattr(exc, "log", "") or traceback.format_exc())
            else:
                ok += 1
                self.signals.job_done.emit(i, out)
        self.signals.finished.emit(ok, failed, self.cancel_token.cancelled)
