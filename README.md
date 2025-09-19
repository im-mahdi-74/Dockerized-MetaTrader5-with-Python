# MetaTrader 5 with Python Data Bridge (Dockerized)

This repository contains the **Dockerfile** and Python scripts used to build the [Docker image of MetaTrader 5 with Python Data Bridge](https://hub.docker.com/repository/docker/immahdi/mt5-python/general).

The Docker image allows you to run a portable MetaTrader 5 (MT5) terminal inside a Windows Server Core container, with two Python services acting as a data bridge for your applications.

It is designed for developers and algorithmic traders who want to programmatically access MT5 account data without running the terminal directly on their local machine.

## Download Large Files 

- [meta.zip](https://drive.google.com/uc?export=download&id=1Uiwa4GjQMksct8ZGqIvhg_WdIGuvaiJu)

  
---

## Features

* **Portable MT5**: Runs a full portable MT5 terminal instance inside the container.
* **Real-time Data Stream**: A Python service (`streamer.py`) streams live account information (balance, equity, open trades, etc.) to a specified WebSocket server.
* **Trade History API**: A Python service (`reporter.py`) provides a REST API endpoint to fetch complete trade history on demand.
* **Headless & Automated**: Fully configured to run in the background on any Docker host.
* **Configurable**: Credentials and endpoints are passed securely via environment variables.

---

## Quick Start

To start the container, provide your MT5 credentials and WebSocket server URI:

```bash
docker run -d --name my-mt5-bot \
  -p 8080:8080 \
  -e MT5_ACCOUNT="YOUR_ACCOUNT_NUMBER" \
  -e MT5_PASSWORD="YOUR_ACCOUNT_PASSWORD" \
  -e MT5_SERVER="YOUR_MT5_SERVER_NAME" \
  -e WEBSOCKET_URI="ws://your-websocket-server-ip:port" \
  immahdi/mt5-python:latest
```

---

## Environment Variables

| Variable           | Description                                                                  | Example                                |
| ------------------ | ---------------------------------------------------------------------------- | -------------------------------------- |
| **MT5\_ACCOUNT**   | Required. Your MetaTrader 5 account number.                                  | `12345678`                             |
| **MT5\_PASSWORD**  | Required. Your MetaTrader 5 account password.                                | `your_secret_password`                 |
| **MT5\_SERVER**    | Required. The name of your broker's server.                                  | `MetaQuotes-Demo`                      |
| **WEBSOCKET\_URI** | Required. Full URI of the WebSocket server for streaming.                    | `ws://192.168.1.100:8765`              |
| **MT5\_PATH**      | Optional. Path to `terminal64.exe` inside container. Defaults automatically. | `C:\Program Files\meta\terminal64.exe` |

---

## Accessing the Services

### 1. Trade History (HTTP API)

The container exposes a REST API on **port 8080**. Fetch trade history with:

```bash
curl http://<docker-host-ip>:8080/history
```

**Response:** JSON object with account number and all closed trades, including details such as `position_id`, `type`, `profit`, `timeopen`, `timeclose`, etc.

---

### 2. Real-time Account Data (WebSocket Stream)

The `streamer.py` service connects to your `WEBSOCKET_URI` and starts sending account updates every second.

Example viewer in Python:

```python
import asyncio
import websockets
import json

WEBSOCKET_URI = "ws://your-websocket-server-ip:port"

async def view_stream():
    async with websockets.connect(WEBSOCKET_URI) as websocket:
        # Introduce this client as a viewer
        await websocket.send(json.dumps({"type": "viewer_hello"}))
        print("Connected as viewer. Waiting for data...")

        async for message in websocket:
            data = json.loads(message)
            print(json.dumps(data, indent=2))

asyncio.run(view_stream())
```

---

## Docker Hub

👉 Prebuilt image is available on Docker Hub: [immahdi/mt5-python](https://hub.docker.com/repository/docker/immahdi/mt5-python/general)

---

## License

This project is released under the MIT License.
