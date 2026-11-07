"""
camera_capture.py
------------------
Runs ON THE RASPBERRY PI 4 with the Pi Camera Module attached.
Captures a leaf photo and uploads it to the /api/pi-diagnose endpoint,
which runs the exact same AI diagnosis pipeline as the website's
"Diagnose" button (DA1 Milvus search + DA2 SQL logging), so a photo
taken directly by the robot gets treated identically to a manual
website upload.

Install on the Pi:
    sudo apt install python3-picamera2
    pip install requests

Usage:
    python3 camera_capture.py --crop-id 3 --server http://<laptop-ip>:5000

Auth: uses the shared PI_API_KEY defined in app/main.py (sent as the
X-API-Key header) -- no farmer login needed, since the Pi isn't a
farmer session. Change PI_API_KEY in main.py before any real
deployment; keep --api-key here in sync with it.
"""

import argparse
import time
import requests

DEFAULT_API_KEY = "change-this-pi-api-key"   # must match PI_API_KEY in app/main.py


def capture_photo(save_path: str):
    """Captures a still image using the Pi Camera Module (picamera2)."""
    from picamera2 import Picamera2

    picam2 = Picamera2()
    config = picam2.create_still_configuration()
    picam2.configure(config)
    picam2.start()
    time.sleep(2)  # let the sensor warm up / auto-exposure settle
    picam2.capture_file(save_path)
    picam2.stop()
    print(f"Captured photo -> {save_path}")


def upload_for_diagnosis(server: str, crop_id: int, image_path: str, api_key: str):
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{server}/api/pi-diagnose/{crop_id}",
            files={"photo": f},
            headers={"X-API-Key": api_key},
            timeout=30,
        )
    print(f"Upload response: HTTP {resp.status_code}")
    try:
        print(resp.json())
    except ValueError:
        print(resp.text)
    return resp


def main():
    parser = argparse.ArgumentParser(description="Capture a leaf photo and send it for diagnosis.")
    parser.add_argument("--crop-id", type=int, required=True)
    parser.add_argument("--server", type=str, required=True, help="e.g. http://192.168.1.20:5000")
    parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY)
    parser.add_argument("--save-path", type=str, default="/tmp/capture.jpg")
    args = parser.parse_args()

    capture_photo(args.save_path)
    upload_for_diagnosis(args.server, args.crop_id, args.save_path, args.api_key)


if __name__ == "__main__":
    main()

