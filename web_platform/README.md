# Trading Web Platform

Django + Channels + Celery web UI for the trading engine. Backtests and live
sessions run **inside the Celery worker** and stream progress to the browser
over a Redis-backed Channels layer. The UI can pause, resume, and stop running
tasks through REST endpoints.

## Architecture

```
Browser  ──WebSocket──▶  Django / Daphne (ASGI)
   │                         ▲
   │ HTTP (start/pause/stop) │ group_send
   ▼                         │
Django / Ninja API  ──AMQP──▶ Redis (broker + channel layer)
                                 ▲
                                 │ group_send from task
                                 │
                            Celery worker ── runs engine
```

- Redis is the Celery broker/result backend **and** the Channels layer.
- Tasks push progress/events via `channel_layer.group_send(...)`; the browser
  receives them through a normal Django Channels consumer.
- Pause / resume / stop is implemented via a DB `control` column that each
  task re-reads at every iteration (no IPC required).

## Prerequisites

- Redis running on `127.0.0.1:6379` (override with `REDIS_HOST` / `REDIS_PORT` /
  `REDIS_URL`).
- Python 3.11+.

## Setup

```bash
uv sync
uv run manage.py migrate
```

## Run (three processes)

```bash
uv run manage.py runserver
```

```bash
# Windows
uv run celery -A web_platform worker --loglevel=info --pool=gevent
uv run celery -A web_platform worker --loglevel=info --pool=eventlet

# Linux/macOS
celery -A web_platform worker --loglevel=info
```

Redis must already be up. That's it — start a backtest in the UI and you'll
see progress stream live from the worker into the browser.

## Task control4

REST endpoints (all accept POST):

| Endpoint                                      | Effect                      |
|-----------------------------------------------|-----------------------------|
| `/api/backtest/runs/<id>/pause/`              | Pause a running backtest    |
| `/api/backtest/runs/<id>/resume/`             | Resume a paused backtest    |
| `/api/backtest/runs/<id>/stop/`               | Stop & persist partial run  |
| `/api/live/pause/<id>/`                       | Pause live session          |
| `/api/live/resume/<id>/`                      | Resume live session         |
| `/api/live/stop/<id>/`                        | Stop live session           |

The Celery task notices the flag on its next loop iteration and emits a
status message on the WebSocket group.

## Windows notes

The default prefork pool (billiard) is broken on Windows 10/11 and throws
`PermissionError: [WinError 5]`. Always use `--pool=gevent` (preferred),
`--pool=threads`, or `--pool=solo` on Windows.

## Eager mode (tests only)

Set `CELERY_TASK_ALWAYS_EAGER=1` to make `.delay()` run inline. The worker is
then not required, but you also lose the realtime WebSocket stream since the
task blocks the request thread.
