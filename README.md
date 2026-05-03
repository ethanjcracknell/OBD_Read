# OBD2 Dashboard

Real-time vehicle telemetry dashboard for the 2011 Ford Falcon XR6.
Reads RPM, speed, coolant temperature, and throttle position via an ELM327 USB adapter and streams them to a browser dashboard over WebSocket.

## Requirements

- Python 3.10 or 3.11+
- Node.js 18+ and npm
- ELM327 USB adapter (Fauvipone V1.5, PIC18F25K80)
- Vehicle: ISO 15765-4 CAN — ensure the HS-CAN switch position is correct

## Quick start (simulated mode, no hardware needed)

```powershell
cd obd2-dashboard
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
python main.py
```

If `python` is not found after activation, run:

```powershell
.\.venv\Scripts\python.exe main.py
```

Open `http://localhost:8080` in your browser.

## Development workflow

Use the Vite development server for frontend iteration:

```powershell
cd obd2-dashboard\frontend
npm install
npm run dev
```

Then start the backend separately:

```powershell
cd ..
python main.py
```

The Vite dev server proxies `/ws` and `/status` to the backend at `http://127.0.0.1:8080`.

## Switching to live mode

1. Plug the ELM327 adapter into the OBD2 port and the laptop USB port.
2. Edit `config.toml`:

   ```toml
   [app]
   mode = "live"

   [obd]
   serial_port = "COM3"
   ```

3. Run `python main.py`.

## Project structure

```
OBD_READ/
├── obd2-dashboard/
│   ├── .gitignore
│   ├── config.toml
│   ├── frontend/             # Vite + React dashboard app
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── src/
│   │   ├── vite.config.js
│   │   └── dist/
│   ├── main.py
│   ├── app/
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── logger.py
│   │   ├── models.py
│   │   ├── poller.py
│   │   └── sources/
│   │       ├── base.py
│   │       ├── live.py
│   │       └── sim.py
│   └── logs/                # generated at runtime
├── PROJECT_CONTEXT.txt
├── README.md
└── requirements.txt
```

## CSV logs

Session files are written to the `logs/` directory, named `session_YYYYMMDDTHHMMSS.csv`.
Logging granularity is configurable in `config.toml`.
