"""
main.py
-------
Smart Crop Disease Monitoring Robot - Farmer Web Portal.

Flow:
  Signup/Login (Farmer)
    -> Add Farm (location, area)
       -> Add Crop (name, variety, planting date)
          -> Upload a leaf photo -> AI diagnosis (Milvus, DA1)
             -> Result + treatment (SQL, DA2) saved as Image + Diagnosis rows
  Reports page uses the 4 stored procedures (disease report, treatment
  recommendation, crop statistics, inspection history).

Run with:
    python3 main.py
(from inside the app/ folder; needs MySQL running with SmartCropDB set up
 -- see database/schema.sql, seed_data.sql, procedures.sql -- and Milvus
 Lite, which is embedded/file-based so needs no separate server.)
"""

import os
import sys
from datetime import date
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image as PILImage

# make ai_module and da3-timescale importable (they live one level up)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from ai_module import milvus_db
from ai_module.embedding import get_embedding
from ai_module.generate_dataset import generate_synthetic_dataset
from ai_module.embedding import get_embedding_from_path

from db import run_query, call_procedure

try:
    from importlib import import_module
    _da3_path = os.path.join(os.path.dirname(__file__), "..", "da3-timescale")
    sys.path.append(_da3_path)
    import db_timescale  # DA3: TimescaleDB/PostgreSQL sensor data
    DA3_AVAILABLE = True
except Exception as _da3_err:
    # DA3's Postgres server may not be running yet -- the rest of the
    # app (DA1 + DA2) still works fine without it.
    DA3_AVAILABLE = False
    print(f"[DA3] sensor module not available yet: {_da3_err}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-this-secret-key-before-real-deployment"

# Simple shared-secret auth for the Raspberry Pi (it has no farmer
# login session, so it authenticates with this key instead). Change
# this before any real deployment; for a lab demo on a closed network
# it's a reasonable, explainable simplification.
PI_API_KEY = "change-this-pi-api-key"


def require_api_key(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.headers.get("X-API-Key") != PI_API_KEY:
            return jsonify({"error": "invalid or missing API key"}), 401
        return view(*args, **kwargs)
    return wrapped

_milvus_client = None


def get_milvus_client():
    """Lazily connect to Milvus Lite and seed the reference dataset once."""
    global _milvus_client
    if _milvus_client is None:
        db_path = os.path.join(BASE_DIR, "..", "crop_disease.db")
        _milvus_client = milvus_db.get_client(db_path)
        milvus_db.create_collection(_milvus_client)
        if milvus_db.count(_milvus_client) == 0:
            _seed_milvus_reference_dataset(_milvus_client)
    return _milvus_client


def _seed_milvus_reference_dataset(client):
    """One-time seed of the reference disease-image bank (DA1 dataset)."""
    from pathlib import Path
    dataset_dir = Path(os.path.join(BASE_DIR, "..", "reference_dataset"))
    records = generate_synthetic_dataset(out_dir=dataset_dir)
    payload = []
    for rec in records:
        vec = get_embedding_from_path(rec["image_path"])
        payload.append({**rec, "embedding": vec.tolist()})
    milvus_db.insert_records(client, payload)


# ------------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------------

def login_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "farmer_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def owns_farm(farm_id: int) -> bool:
    row = run_query(
        "SELECT Farm_ID FROM Farm WHERE Farm_ID=%s AND Farmer_ID=%s",
        (farm_id, session.get("farmer_id")), fetch="one",
    )
    return row is not None


def owns_crop(crop_id: int) -> bool:
    row = run_query(
        """SELECT c.Crop_ID FROM Crop c JOIN Farm f ON c.Farm_ID = f.Farm_ID
           WHERE c.Crop_ID=%s AND f.Farmer_ID=%s""",
        (crop_id, session.get("farmer_id")), fetch="one",
    )
    return row is not None


# ------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------

@app.route("/")
def index():
    if "farmer_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        phone = request.form["phone"].strip()
        address = request.form.get("address", "").strip()
        password = request.form["password"]

        existing = run_query("SELECT Farmer_ID FROM Farmer WHERE Phone=%s", (phone,), fetch="one")
        if existing:
            flash("An account with this phone number already exists.", "error")
            return render_template("register.html")

        pw_hash = generate_password_hash(password)
        farmer_id = run_query(
            "INSERT INTO Farmer (Name, Phone, Address, Password) VALUES (%s,%s,%s,%s)",
            (name, phone, address, pw_hash), fetch="none",
        )
        session["farmer_id"] = farmer_id
        session["farmer_name"] = name
        flash("Account created successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form["phone"].strip()
        password = request.form["password"]

        farmer = run_query("SELECT * FROM Farmer WHERE Phone=%s", (phone,), fetch="one")
        if farmer and check_password_hash(farmer["Password"], password):
            session["farmer_id"] = farmer["Farmer_ID"]
            session["farmer_name"] = farmer["Name"]
            return redirect(url_for("dashboard"))
        flash("Invalid phone number or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    farms = run_query(
        "SELECT * FROM Farm WHERE Farmer_ID=%s ORDER BY Farm_ID DESC",
        (session["farmer_id"],),
    )
    for farm in farms:
        farm["crops"] = run_query(
            "SELECT * FROM Crop WHERE Farm_ID=%s ORDER BY Crop_ID DESC",
            (farm["Farm_ID"],),
        )
    return render_template("dashboard.html", farms=farms)


# ------------------------------------------------------------------
# Farm management
# ------------------------------------------------------------------

@app.route("/farm/new", methods=["GET", "POST"])
@login_required
def new_farm():
    if request.method == "POST":
        location = request.form["location"].strip()
        area = request.form["area"].strip()
        run_query(
            "INSERT INTO Farm (Farmer_ID, Location, Area) VALUES (%s,%s,%s)",
            (session["farmer_id"], location, area), fetch="none",
        )
        flash("Farm added.", "success")
        return redirect(url_for("dashboard"))
    return render_template("farm_new.html")


@app.route("/farm/<int:farm_id>")
@login_required
def farm_detail(farm_id):
    if not owns_farm(farm_id):
        flash("Farm not found.", "error")
        return redirect(url_for("dashboard"))
    farm = run_query("SELECT * FROM Farm WHERE Farm_ID=%s", (farm_id,), fetch="one")
    crops = run_query("SELECT * FROM Crop WHERE Farm_ID=%s ORDER BY Crop_ID DESC", (farm_id,))
    return render_template("farm_detail.html", farm=farm, crops=crops)


# ------------------------------------------------------------------
# Crop management
# ------------------------------------------------------------------

@app.route("/crop/new", methods=["GET", "POST"])
@login_required
def new_crop():
    farm_id = request.values.get("farm_id", type=int)
    if not farm_id or not owns_farm(farm_id):
        flash("Select a valid farm first.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        crop_name = request.form["crop_name"].strip()
        variety = request.form.get("variety", "").strip()
        planting_date = request.form.get("planting_date") or date.today().isoformat()
        run_query(
            "INSERT INTO Crop (Farm_ID, Crop_Name, Variety, Planting_Date) VALUES (%s,%s,%s,%s)",
            (farm_id, crop_name, variety, planting_date), fetch="none",
        )
        flash("Crop added.", "success")
        return redirect(url_for("farm_detail", farm_id=farm_id))

    return render_template("crop_new.html", farm_id=farm_id)


@app.route("/crop/<int:crop_id>/history")
@login_required
def crop_history(crop_id):
    if not owns_crop(crop_id):
        flash("Crop not found.", "error")
        return redirect(url_for("dashboard"))
    crop = run_query("SELECT * FROM Crop WHERE Crop_ID=%s", (crop_id,), fetch="one")
    result_sets = call_procedure("GetInspectionHistory", (crop_id,))
    history = result_sets[0] if result_sets else []
    return render_template("crop_history.html", crop=crop, history=history)


# ------------------------------------------------------------------
# Diagnosis (the AI + Milvus part) - shared core used by both the
# website upload form AND the Raspberry Pi camera endpoint below.
# ------------------------------------------------------------------

def run_diagnosis(crop_id: int, photo_file, original_filename: str):
    """
    Saves the uploaded photo, runs it through Milvus (DA1), and logs
    the result into MySQL (DA2: Image + Diagnosis + Treatment lookup).
    Returns a dict with everything a caller needs to render/report
    the result, or None if diagnosis wasn't possible.
    """
    filename = secure_filename(f"crop{crop_id}_{original_filename}")
    save_path = os.path.join(UPLOAD_DIR, filename)
    photo_file.save(save_path)

    img = PILImage.open(save_path)
    query_vec = get_embedding(img)
    client = get_milvus_client()
    hits = milvus_db.search_similar(client, query_vec, top_k=1)

    if not hits:
        return None

    best = hits[0]
    e = best["entity"]
    similarity_pct = round(best["distance"] * 100, 2)

    rel_path = f"uploads/{filename}"
    image_id = run_query(
        "INSERT INTO Image (Crop_ID, Image_Path, Capture_Date, Milvus_Vector_ID) VALUES (%s,%s,%s,%s)",
        (crop_id, rel_path, date.today().isoformat(), str(best["image_id"])),
        fetch="none",
    )

    disease_row = run_query(
        "SELECT * FROM Disease WHERE Crop_Name=%s AND Disease_Name=%s",
        (e["crop_name"], e["disease_name"]), fetch="one",
    )

    treatment_row = None
    if disease_row:
        run_query(
            "INSERT INTO Diagnosis (Image_ID, Disease_ID, Similarity_Score) VALUES (%s,%s,%s)",
            (image_id, disease_row["Disease_ID"], similarity_pct), fetch="none",
        )
        treatment_row = run_query(
            "SELECT * FROM Treatment WHERE Disease_ID=%s", (disease_row["Disease_ID"],), fetch="one",
        )

    return {
        "entity": e, "similarity": similarity_pct,
        "treatment": treatment_row, "image_path": rel_path,
    }


@app.route("/diagnose/<int:crop_id>", methods=["GET", "POST"])
@login_required
def diagnose(crop_id):
    if not owns_crop(crop_id):
        flash("Crop not found.", "error")
        return redirect(url_for("dashboard"))
    crop = run_query("SELECT * FROM Crop WHERE Crop_ID=%s", (crop_id,), fetch="one")

    if request.method == "POST":
        photo = request.files.get("photo")
        if not photo or photo.filename == "":
            flash("Please choose an image to upload.", "error")
            return redirect(url_for("diagnose", crop_id=crop_id))

        result = run_diagnosis(crop_id, photo, photo.filename)
        if result is None:
            flash("Could not diagnose this image (reference database empty).", "error")
            return redirect(url_for("crop_history", crop_id=crop_id))

        return render_template(
            "diagnose_result.html", crop=crop, entity=result["entity"],
            similarity=result["similarity"], treatment=result["treatment"],
            image_path=result["image_path"],
        )

    return render_template("diagnose.html", crop=crop)


# ------------------------------------------------------------------
# Raspberry Pi endpoints (DA3 hardware) - API-key protected instead
# of session-login protected, since the Pi has no farmer session.
# ------------------------------------------------------------------

@app.route("/api/pi-diagnose/<int:crop_id>", methods=["POST"])
@require_api_key
def api_pi_diagnose(crop_id):
    """Same diagnosis pipeline as /diagnose, called by camera_capture.py on the Pi."""
    photo = request.files.get("photo")
    if not photo or photo.filename == "":
        return jsonify({"error": "no photo uploaded"}), 400

    crop = run_query("SELECT * FROM Crop WHERE Crop_ID=%s", (crop_id,), fetch="one")
    if not crop:
        return jsonify({"error": "crop not found"}), 404

    result = run_diagnosis(crop_id, photo, photo.filename)
    if result is None:
        return jsonify({"error": "reference database empty, could not diagnose"}), 500

    return jsonify({
        "crop": crop["Crop_Name"],
        "disease": result["entity"]["disease_name"],
        "severity": result["entity"]["severity"],
        "similarity": result["similarity"],
        "treatment": result["treatment"]["Treatment_Name"] if result["treatment"] else None,
        "dosage": result["treatment"]["Dosage"] if result["treatment"] else None,
    })


@app.route("/api/sensor-reading", methods=["POST"])
@require_api_key
def api_sensor_reading():
    """Called by sensor_reader.py on the Pi every few minutes (DA3)."""
    if not DA3_AVAILABLE:
        return jsonify({"error": "sensor database not configured on this server"}), 503

    data = request.get_json(force=True, silent=True) or {}
    farm_id = data.get("farm_id")
    sensor_type = data.get("sensor_type")
    value = data.get("value")
    unit = data.get("unit")

    if not all([farm_id, sensor_type, value is not None, unit]):
        return jsonify({"error": "farm_id, sensor_type, value, unit are all required"}), 400

    db_timescale.insert_reading(farm_id, sensor_type, value, unit)
    return jsonify({"status": "ok"})


@app.route("/farm/<int:farm_id>/sensors")
@login_required
def farm_sensors(farm_id):
    """Dashboard: latest readings + hourly trend + any active alerts (DA3)."""
    if not owns_farm(farm_id):
        flash("Farm not found.", "error")
        return redirect(url_for("dashboard"))
    farm = run_query("SELECT * FROM Farm WHERE Farm_ID=%s", (farm_id,), fetch="one")

    if not DA3_AVAILABLE:
        flash("Sensor database is not connected yet.", "error")
        return render_template("farm_sensors.html", farm=farm, latest=[], trend=[], alerts=[], da3_available=False)

    latest = db_timescale.latest_readings(farm_id)
    trend = db_timescale.hourly_averages(farm_id, "soil_moisture", hours=24)
    alerts = db_timescale.check_alerts(farm_id)
    return render_template("farm_sensors.html", farm=farm, latest=latest, trend=trend, alerts=alerts, da3_available=True)


# ------------------------------------------------------------------
# Reports (the other 3 stored procedures)
# ------------------------------------------------------------------

@app.route("/reports")
@login_required
def reports():
    farmer_id = session["farmer_id"]

    disease_report_sets = call_procedure("GetDiseaseReport", (farmer_id,))
    disease_rows = disease_report_sets[0] if len(disease_report_sets) > 0 else []
    severity_tally = disease_report_sets[1][0] if len(disease_report_sets) > 1 and disease_report_sets[1] else {}

    crop_stats_sets = call_procedure("GetCropStatistics", (farmer_id,))
    crop_stats = crop_stats_sets[0] if crop_stats_sets else []

    return render_template(
        "reports.html", disease_rows=disease_rows,
        severity_tally=severity_tally, crop_stats=crop_stats,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
