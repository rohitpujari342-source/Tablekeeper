# Tablekeeper — Stage 3

## Build and Run

```sh
docker build -t tablekeeper-stage-3 .
docker run --rm -p 8080:8080 -e PORT=8080 tablekeeper-stage-3
```

## Health Check

```sh
curl http://localhost:8080/health
```

## Local Development

```sh
python server.py
```
