# Smart Crop Disease Monitoring Robot — Farmer Web Portal

**One project, three databases, each doing what it's best at:**
- **Milvus** (DA1) — image embeddings + vector similarity search: identifies
  the disease from a leaf photo.
- **MySQL** (DA2) — Farmer accounts, farms, crops, disease/treatment master
  data, every diagnosis logged over time, 4 stored procedures.
- **TimescaleDB/PostgreSQL** (DA3) — live sensor stream from the Raspberry Pi
  (soil moisture, temperature, humidity) — a genuinely different data shape
  (continuous time-series) that a relational table isn't built for.

All three are wired into one Flask app (`app/main.py`).

## What the app does

1. A farmer **signs up** with name, phone, address, password.
2. They **add a farm** (location, area) and **add crops** to it.
3. When a crop looks sick, they **upload a leaf photo** (from the website,
   or from the Pi camera directly). The app:
   - generates a 512-D ResNet18 embedding of the photo,
   - searches Milvus for the most visually similar known disease image,
   - looks up that disease's treatment in MySQL,
   - logs the result (`Image` + `Diagnosis` rows) so it shows up in history/reports.
4. **Reports page** — disease report, severity breakdown, and per-crop
   statistics, served by MySQL stored procedures.
5. **Sensor Dashboard** (per farm) — live soil moisture / temperature /
   humidity from the Pi's sensors, an hourly trend, and threshold alerts.

## Folder structure

```
smart-crop-webapp/
├── database/                       DA2 (MySQL)
│   ├── schema.sql                  Farmer, Farm, Crop, Disease, Treatment, Image, Diagnosis
│   ├── seed_data.sql                8 disease/treatment master records
│   └── procedures.sql               4 required PL/SQL-style procedures
├── ai_module/                       DA1 (Milvus)
│   ├── milvus_db.py                 create/insert/search/filter
│   ├── embedding.py                 ResNet18 image -> 512-D vector
│   └── generate_dataset.py          Synthetic reference disease-image bank
├── da3-timescale/                    DA3 (TimescaleDB/PostgreSQL)
│   ├── database/
│   │   ├── schema_timescale.sql      SensorReading, SensorThreshold tables
│   │   └── queries.sql                Core time-series operations (insert, latest,
│   │                                   time-range, hourly aggregation, alerts, retention)
│   ├── db_timescale.py               Connection helper used by the Flask app
│   └── pi_scripts/                    Code that runs ON the Raspberry Pi 4
│       ├── sensor_reader.py            Reads DHT11 + soil moisture, POSTs readings
│       └── camera_capture.py           Captures a photo, POSTs it for diagnosis
├── app/                              The unified Flask web app
│   ├── main.py                        Routes: auth, farm/crop CRUD, diagnose, reports, sensors
│   ├── db.py                          MySQL connection + stored-procedure helper
│   ├── templates/                     All HTML pages
│   └── static/uploads/                Uploaded leaf photos land here
├── setup_database.sh                 One-shot MySQL setup (DA2)
├── setup_timescale.sh                 One-shot PostgreSQL setup (DA3)
├── requirements.txt
└── report/                            DA1 report (EER, normalization, comparative analysis)
```

## Setup (do this once)

### 1. Install both database servers

```bash
# Ubuntu/Debian (or Raspberry Pi OS, if you run the app itself on the Pi)
sudo apt update
sudo apt install mysql-server postgresql
```

### 2. Set up MySQL (DA2)

```bash
cd smart-crop-webapp
chmod +x setup_database.sh
./setup_database.sh
```
Creates user `cropapp` / password `cropapp_pass`, database `SmartCropDB`,
loads schema + seed data + stored procedures.

### 3. Set up PostgreSQL (DA3)

```bash
chmod +x setup_timescale.sh
./setup_timescale.sh
```
Creates the same `cropapp` user in Postgres, database `smartfarmsensors`,
loads the sensor schema. (Real TimescaleDB extension is optional — see the
comment block at the top of `da3-timescale/database/schema_timescale.sql`
for the exact install command. Plain PostgreSQL works fine for the demo;
the extension just adds automatic time-partitioning under the hood.)

**Windows note:** the `.sh` scripts need bash (Git Bash, WSL, or run the SQL
commands manually — see the comments inside each script; they're just a few
`CREATE USER` / `CREATE DATABASE` / load-the-.sql-file commands).

### 4. Python environment (for the laptop/server running the Flask app)

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

The first time you run the app, PyTorch downloads the pretrained ResNet18
weights (~45 MB) — make sure you have internet for that first run.

### 5. Run the app

```bash
cd app
python main.py
```
Open **http://localhost:5000**.

## Setting up the Raspberry Pi (DA3 hardware)

The Pi is a **separate device on the same network** as the laptop/server
running the Flask app — it doesn't run any database itself, it just reads
sensors/captures photos and POSTs the data over HTTP.

**Wiring:**
- **DHT11** data pin → GPIO4 (physical pin 7)
- **Soil moisture sensor** → MCP3008 ADC channel 0 → SPI (Pi has no native
  analog input) — see the wiring comment block at the top of `sensor_reader.py`
- **Pi Camera Module** → the CSI camera port

**On the Pi:**
```bash
pip install adafruit-circuitpython-dht spidev requests
sudo apt install libgpiod2 python3-picamera2
```

**Find your laptop's IP** (where Flask is running) — on the laptop, run
`ipconfig` (Windows) or `ip addr` (Linux) and note the local network IP
(e.g. `192.168.1.20`).

**Run the sensor loop** (leave running, reads every 5 min):
```bash
python3 sensor_reader.py --farm-id 1 --server http://192.168.1.20:5000
```
No hardware wired up yet? Test the pipeline with fake data:
```bash
python3 sensor_reader.py --farm-id 1 --server http://192.168.1.20:5000 --simulate --once
```

**Capture + diagnose a photo from the Pi:**
```bash
python3 camera_capture.py --crop-id 3 --server http://192.168.1.20:5000
```

Both scripts authenticate with a shared `X-API-Key` header (the Pi has no
farmer login) — the key is `change-this-pi-api-key` by default, set in
`app/main.py` (`PI_API_KEY`) and in both Pi scripts (`DEFAULT_API_KEY`).
Change it to something real before any actual deployment, keeping both
sides in sync.

## Using a real leaf-image dataset instead of the synthetic one

`ai_module/generate_dataset.py` builds placeholder images so the whole
pipeline works without needing to source a real dataset first. For your
final demo, swap in a real one (e.g. PlantVillage on Kaggle) using
`load_real_dataset()` from the same file — see its docstring.

## Mapping to your DA rubric

| Rubric item | DA1 (Milvus) | DA2 (MySQL) | DA3 (TimescaleDB) |
|---|---|---|---|
| Schema/model design | Collection schema in `milvus_db.py` | `database/schema.sql` | `da3-timescale/database/schema_timescale.sql` |
| Sample dataset | `generate_dataset.py` | `seed_data.sql` | seed via `sensor_reader.py --simulate` |
| Core operations | create/insert/search/filter | 4 stored procedures (`procedures.sql`) | insert / latest / time-range / hourly aggregation / threshold alert / retention (`queries.sql`) |
| Comparative analysis | Milvus vs relational — `report/REPORT_DA1_EER_and_Milvus.md` | (same report) | TimescaleDB vs plain MySQL for continuous sensor streams — to be added when DA3 is finalized |
| PL/SQL: Disease report / Treatment recommendation / Crop statistics / Inspection history | — | all 4 in `procedures.sql`, used in `main.py` | — |

EER model + normalization (shared foundation for all three) — carried
forward unchanged in `report/REPORT_DA1_EER_and_Milvus.md`.

## Notes / things to double-check before your demo

- **Change `app.secret_key` and `PI_API_KEY`** in `main.py` before any real
  deployment (both are placeholders). Fine as-is for a college demo.
- DB passwords are stored in plaintext in `app/db.py` / `da3-timescale/db_timescale.py`
  for simplicity — call this out as a known limitation in your report if asked.
- Farmer account passwords ARE hashed (`werkzeug.security`) — that part's
  production-appropriate.
- If the Postgres server isn't running/configured, the app still works fine
  for DA1+DA2 — the sensor dashboard just shows "not connected" instead of
  crashing the whole app.
