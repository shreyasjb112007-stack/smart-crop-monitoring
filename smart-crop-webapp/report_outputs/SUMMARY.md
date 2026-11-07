# Smart Crop Disease Monitoring Robot - Execution Summary

## 1. Project Execution Overview
- **Project Directory**: `smart-crop-webapp`
- **Execution Date**: 2026-10-20
- **Platform**: Windows 11 (PowerShell, Python 3.12)
- **Databases**:
  - MySQL 8.0 (`cropapp` / `cropapp_pass` @ `127.0.0.1:3306`, DB: `SmartCropDB`)
  - PostgreSQL 16 (`cropapp` / `cropapp_pass` @ `127.0.0.1:5432`, DB: `smartfarmsensors`)
- **Flask Web Server**: Running in background on `0.0.0.0:5000`

---

## 2. Entity Identifiers Used
- **Farmer_ID**: `2` (Name: "Demo Farmer", Phone: "9000000100", Address: "Chennai")
- **Farm_ID**: `2` (Location: "Demo Farm Vellore", Area: 2.5 acres)
- **Crop_ID**: `2` (Crop: "Tomato", Variety: "Roma", Planting Date: "2026-06-01")

---

## 3. Step Execution Status

| Step | Description | Status | Output Artifact(s) |
|---|---|---|---|
| **Step 0** | Create `report_outputs/` directory | **PASS** | `report_outputs/` |
| **Step 1** | Milvus Lite Crop Disease Vector DB Test (Report 9.3) | **PASS** | `9.3_milvus_output.txt` |
| **Step 2** | PostgreSQL Schema Verification & Table Inspection (Report 9.5) | **PASS** | `9.5_dt_output.txt`<br>`9.5_describe_sensorreading.txt`<br>`9.5_describe_sensorthreshold.txt` |
| **Step 3** | PostgreSQL Sensor Data Seeding & Queries (Report 9.6) | **PASS** | `9.6_row_count.txt`<br>`9.6_latest_reading.txt`<br>`9.6_threshold_alert.txt` |
| **Step 4** | Start Flask Web Server & Health Check (Report 9.4) | **PASS** | `startup_check.txt` |
| **Step 5** | Website Demo Data Generation, ResNet18 Diagnosis & Sensor API | **PASS** | `9.4_diagnosis_result.html`<br>`page_dashboard.html`<br>`page_crop_history.html`<br>`page_reports.html`<br>`page_sensor_dashboard.html`<br>`api_checks.txt` |
| **Step 6** | MySQL Tables & Stored Procedures (Reports 9.1 & 9.2) | **PASS** | `9.1_show_tables.txt`<br>`9.2_disease_report.txt`<br>`9.2_crop_statistics.txt`<br>`9.2_inspection_history.txt`<br>`9.2_treatment.txt` |
| **Step 7** | Website Full UI Screenshots (Playwright) | **PASS** | `screenshots/login.png`<br>`screenshots/register.png`<br>`screenshots/dashboard.png`<br>`screenshots/add_crop.png`<br>`screenshots/diagnose_result.png`<br>`screenshots/crop_history.png`<br>`screenshots/reports.png`<br>`screenshots/sensor_dashboard.png` |
| **Step 8** | Summary Documentation | **PASS** | `SUMMARY.md` |

---

## 4. Created Files Inventory

### Root `report_outputs/` Files:
1. `9.1_show_tables.txt`: MySQL `SHOW TABLES;` listing all tables in `SmartCropDB`.
2. `9.2_crop_statistics.txt`: Output of `CALL GetCropStatistics(2);`.
3. `9.2_disease_report.txt`: Output of `CALL GetDiseaseReport(2);`.
4. `9.2_inspection_history.txt`: Output of `CALL GetInspectionHistory(2);`.
5. `9.2_treatment.txt`: Output of `CALL GetTreatmentRecommendation('Tomato', 'Early Blight');`.
6. `9.3_milvus_output.txt`: Milvus Lite vector database creation, collection schema, 512-dim embedding indexing, and vector insertion output.
7. `9.4_diagnosis_result.html`: HTML response from the ResNet18-powered diagnosis endpoint `/diagnose/2`.
8. `9.5_describe_sensorreading.txt`: PostgreSQL `\d sensorreading` schema description.
9. `9.5_describe_sensorthreshold.txt`: PostgreSQL `\d sensorthreshold` schema description.
10. `9.5_dt_output.txt`: PostgreSQL `\dt` listing relations in `smartfarmsensors`.
11. `9.6_latest_reading.txt`: Output of latest reading query (Query 2 from `queries.sql`).
12. `9.6_row_count.txt`: Output of `SELECT COUNT(*) FROM SensorReading;` (10 rows).
13. `9.6_threshold_alert.txt`: Output of threshold alert query (Query 5 from `queries.sql`), alerting on low soil moisture (22.00% < 35.00%).
14. `api_checks.txt`: Responses for `POST /api/sensor-reading` without API key (401 Unauthorized) and with valid `X-API-Key` (200 OK).
15. `startup_check.txt`: HTTP 200 response verification for `GET http://127.0.0.1:5000/login`.
16. `page_dashboard.html`: Rendered HTML for `/dashboard`.
17. `page_crop_history.html`: Rendered HTML for `/crop/2/history`.
18. `page_reports.html`: Rendered HTML for `/reports`.
19. `page_sensor_dashboard.html`: Rendered HTML for `/farm/2/sensors`.
20. `ERRORS.txt`: Logged errors and tracebacks during execution.
21. `SUMMARY.md`: This execution summary file.

### `report_outputs/screenshots/` (Playwright PNG Captures):
1. `login.png`: Login page interface (`/login`).
2. `register.png`: Registration page interface (`/register`).
3. `dashboard.png`: Farmer dashboard with farms and crops (`/dashboard`).
4. `add_crop.png`: New crop form (`/crop/new?farm_id=2`).
5. `diagnose_result.png`: Leaf diagnosis inspection results page with AI predictions.
6. `crop_history.png`: Historical crop health records and inspections (`/crop/2/history`).
7. `reports.png`: Disease analytics and summary report page (`/reports`).
8. `sensor_dashboard.png`: Farm sensor readings and telemetry threshold dashboard (`/farm/2/sensors`).

---

## 5. Contents of ERRORS.txt

```
Step 5 error:
Traceback (most recent call last):
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 1430, in getresponse
    response.begin()
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 331, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 292, in _read_status
    line = str(self.fp.readline(_MAXLINE + 1), "iso-8859-1")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\socket.py", line 720, in readinto
    return self._sock.recv_into(b)
           ^^^^^^^^^^^^^^^^^^^^^^^
ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\adapters.py", line 696, in send
    resp = conn.urlopen(
           ^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connectionpool.py", line 842, in urlopen
    retries = retries.increment(
              ^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\util\retry.py", line 498, in increment
    raise reraise(type(error), error, _stacktrace)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\util\util.py", line 38, in reraise
    raise value.with_traceback(tb)
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 1430, in getresponse
    response.begin()
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 331, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 292, in _read_status
    line = str(self.fp.readline(_MAXLINE + 1), "iso-8859-1")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\socket.py", line 720, in readinto
    return self._sock.recv_into(b)
           ^^^^^^^^^^^^^^^^^^^^^^^
urllib3.exceptions.ProtocolError: ('Connection aborted.', ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None))

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\Users\shrey\OneDrive\Documents\files\projects\dbs\smart-crop-webapp(final)\smart-crop-webapp\step5_runner.py", line 16, in <module>
    diag_res = s.post(f"http://127.0.0.1:5000/diagnose/{crop_id}", files={"photo": ("test_leaf.jpg", f, "image/jpeg")})
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\sessions.py", line 712, in post
    return self.request("POST", url, data=data, json=json, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\sessions.py", line 651, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\sessions.py", line 784, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\shrey\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\adapters.py", line 711, in send
    raise ConnectionError(err, request=request)
requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None))
```

*Note on error*: Writing temporary helper script files into the workspace directory triggered Flask's reloader mid-request, leading to a momentary connection reset. The script was moved to `%TEMP%` outside the workspace watch tree and executed cleanly without interrupting the server, successfully generating all required Step 5 outputs.
