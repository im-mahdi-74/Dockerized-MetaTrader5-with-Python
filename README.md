# Dockerized MetaTrader 5 with Python Data Bridge

**This repository provides everything needed to run a portable MetaTrader 5 (MT5) inside Docker and expose MT5 data to your apps via a WebSocket stream and a REST trade-history API.**

---

## What this repo does

* Runs a **portable MT5 terminal** inside a Windows container.
* Streams live account information (balance, equity, open trades, etc.) from each MT5 instance using `streamer.py` to a central **WebSocket Hub (router)**.
* Exposes a **REST API** (`reporter.py`) that returns the full trade history on demand (HTTP `/history`).
* Intended audience: company or developers and algorithmic traders who want programmatic access to MT5 data without running the terminal locally.

---

## Quick overview (short)

* Build image locally: `docker build -t immahdi/mt5-python:latest .`
* Or pull the prebuilt image from Docker Hub: `docker pull immahdi/mt5-python:latest`
* Run a central WebSocket Hub on a server (see `websocket_hub.py`).
* Run one or more MT5 containers (or hosts) that run `streamer.py` and send their data to the Hub.
* Use a viewer client to connect to the Hub and receive live data; use `/history` on the MT5 container to fetch trade history.

Docker Hub: [https://hub.docker.com/repository/docker/immahdi/mt5-python/general](https://hub.docker.com/repository/docker/immahdi/mt5-python/general)

---

## Files in repository (root) — what each file is for

* **Dockerfile** — builds the Windows container image with portable MT5 and the Python services.
* **streamer.py** — inside-container service that reads MT5 account state and open trades and forwards JSON messages to the WebSocket Hub (as a producer/streamer).
* **reporter.py** — exposes a small REST API (port `8080`) with an endpoint `/history` that returns closed-trade history as JSON.
* **websocket\_hub.py** — the central WebSocket Hub/Router. It accepts connections from multiple streamers and multiple viewers and broadcasts streamer messages to viewers. **Place this file in the repository root and run it on the machine you want to host the hub.**
* **start.ps1** — optional Windows PowerShell startup script used inside the container to launch services.
* **meta.zip** — (large) the portable MetaTrader 5 files. *Not checked in by default.* Download and place this file in the repo root before building the image if you plan to build locally. Public download link provided below.
* **python-3.11.4-amd64.exe** — included installer . This is provided to install Python inside the container if needed.

> **Note:** `meta.zip` you should download the file and place it at the project root before building locally.

Download `meta.zip` (place in repo root):

- [meta.zip](https://drive.google.com/uc?export=download&id=1Uiwa4GjQMksct8ZGqIvhg_WdIGuvaiJu)

---

## How to run (recommended workflow)

### 1) Run the WebSocket Hub (on a server or a user machine)

```bash
git clone https://github.com/im-mahdi-74/Dockerized-MetaTrader5-with-Python.git
cd Dockerized-MetaTrader5-with-Python
python -m pip install --user websockets
python websocket_hub.py
```

Hub listens on `ws://0.0.0.0:8765` by default.

### 2) Build the Docker image locally (optional)

If you prefer to build the image yourself (you must have `meta.zip` at repository root):

```bash
# from repository root where Dockerfile and meta.zip are located
docker build -t immahdi/mt5-python:latest .
```

**Or** pull the prebuilt image from Docker Hub:

```bash
docker pull immahdi/mt5-python:latest
```

### 3) Run the MT5 container and connect it to the Hub

```bash
docker run -d --name my-mt5-bot \
  -p 8080:8080 \
  -e MT5_ACCOUNT="YOUR_ACCOUNT_NUMBER" \
  -e MT5_PASSWORD="YOUR_ACCOUNT_PASSWORD" \
  -e MT5_SERVER="YOUR_MT5_SERVER_NAME" \
  -e WEBSOCKET_URI="ws://<hub-server-ip>:8765" \
  immahdi/mt5-python:latest
```

* Set `WEBSOCKET_URI` to the Hub address where `websocket_hub.py` is running.
* Each MT5 instance/container that should stream live account and open-trades data **must run `streamer.py`** (the image’s startup script runs it automatically if configured). If you are running manually inside the container, start `streamer.py` so the container becomes a streamer for the Hub.

### 4) View live data (viewer client)

Run this Python snippet on the viewer machine to connect and receive live messages from the Hub:

```python
import asyncio
import websockets
import json

WEBSOCKET_URI = "ws://<hub-server-ip>:8765"

async def view_stream():
    async with websockets.connect(WEBSOCKET_URI) as websocket:
        await websocket.send(json.dumps({"type": "viewer_hello"}))
        print("Connected as viewer. Receiving live data...")
        async for message in websocket:
            print(json.dumps(json.loads(message), indent=2))

asyncio.run(view_stream())
```

> Important: for each account you want to stream, the corresponding MT5 container must be running `streamer.py` so it connects to the Hub as a `streamer_hello` producer.

### 5) Fetch trade history (HTTP)

From any client you can ask the MT5 container for trade history:

```bash
curl http://<docker-host-ip>:8080/history
```

Response: JSON object with `account_number` and the list of closed trades with fields such as `position_id` , `type` , `ticketopen` , `priceopen`, `timeopen`, `volumeopen` , `ticketclose` , `priceclose` , `timeclose` , `volumeclose` , `profit` ... , etc.

---

## Networking & ports

* WebSocket Hub: `8765` (TCP)
* REST API (reporter): `8080` (HTTP)

Make sure these ports are reachable between the Hub and MT5 containers/hosts and between viewers and the Hub.

---

## Hardware requirements

* **Minimum:** 2 GB RAM, 1 vCPU
* **Recommended:** 3 GB RAM, 2 vCPU

---

## Contacts & contribution

If you have issues or want to contribute, please reach out:

* Telegram: `@immahdi74`
* LinkedIn: https://www.linkedin.com/in/immahdi74
* Email: mahdi.mosavi.nsa@gmail.com

Contributions are welcome — open a PR or open an issue.

---

## License

This project is released under the MIT License.

---

