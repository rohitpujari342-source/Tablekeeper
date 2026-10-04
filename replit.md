# Tablekeeper Stage 1 on Replit

## Run the HTTP service

Python 3.12 is configured in `.replit`. Click **Run** to start the Stage 1 API
on port 5000, or run it manually from the repository root:

```sh
PORT=5000 python stage-1/server.py
```

The service listens on `0.0.0.0` and reports readiness at `GET /health`.

## Run tests

```sh
python -m unittest discover -s stage-1/tests -v
```

## Container

The repository root includes a `Dockerfile` and `RUN.md` with the standalone
build and start commands. The container defaults to port 8080; set `PORT` to
override it. Runtime state is in memory and is not preserved across restarts.

## Specification and dependencies

This implements the [official Dark Factory Tablekeeper Stage 1
specification](https://github.com/band-ai/dark-factory-wearedevs/blob/main/tablekeeper/spec/stage-1.md).
The service uses Python's standard library and the existing Stage 1 domain
helpers. The Docker image includes the `tzdata` package so IANA timezone
behavior is available even when the container has no system timezone database.
No API keys or external runtime services are required. The HTTP service and test
suite are Stage 1 only; later stages are not included.