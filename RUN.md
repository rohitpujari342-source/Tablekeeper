# Run Tablekeeper Stage 1

Build and start the standalone HTTP service with Docker:

```sh
docker build -t tablekeeper-stage1 .
docker run --rm -p 8080:8080 -e PORT=8080 tablekeeper-stage1
```

The health endpoint is available at `http://localhost:8080/health`. The container
includes all runtime dependencies; it does not call external services and keeps
its state in memory, so state is reset when the container restarts.

For local development from the repository root:

```sh
PORT=8080 python stage-1/server.py
```

Run the test suite with:

```sh
python -m unittest discover -s stage-1/tests -v
```