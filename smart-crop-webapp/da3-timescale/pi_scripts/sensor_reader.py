"""
sensor_reader.py
-----------------
Runs ON THE RASPBERRY PI 4. Reads a DHT11 (temperature + humidity)
and a soil moisture sensor, then sends each reading to the Flask
app, which writes them into TimescaleDB/PostgreSQL (SensorReading
table).

Wiring (standard lab setup):
  DHT11 data pin      -> GPIO4 (physical pin 7), with a 10k pull-up
                          resistor between data and 3.3V (most DHT11
                          breakout boards already include this on-board).
  Soil moisture sensor -> analog output pin -> MCP3008 ADC (channel 0)
                          -> SPI on the Pi (Raspberry Pi has no native
                          analog input, hence the ADC chip).
      MCP3008: VDD->3.3V, VREF->3.3V, AGND->GND, DGND->GND,
               CLK->GPIO11(SCLK), DOUT->GPIO9(MISO), DIN->GPIO10(MOSI),
               CS->GPIO8(CE0)

Install on the Pi:
    pip install adafruit-circuitpython-dht spidev requests
    sudo apt install libgpiod2      # needed by adafruit-circuitpython-dht

Run:
    python3 sensor_reader.py --farm-id 1 --server http://<laptop-ip>:5000
    (leave it running -- it loops forever, reading every INTERVAL_SECONDS)

If you don't have the hardware wired up yet, run with --simulate to
send realistic fake readings instead -- useful for testing the web
app / database side independently of the hardware.
"""

import argparse
import time
import random
import requests

INTERVAL_SECONDS = 60 * 5   # one reading every 5 minutes (matches lab cadence)
DEFAULT_API_KEY = "change-this-pi-api-key"   # must match PI_API_KEY in app/main.py


def read_real_sensors():
    """Reads the actual DHT11 + soil moisture sensor. Only works when
    run on a Raspberry Pi with the hardware wired up as described above."""
    import board
    import adafruit_dht
    import spidev

    # DHT11 on GPIO4 (adafruit_dht.DHT11 -- swap to DHT22 here if you
    # ever upgrade the sensor; wiring/pin stays the same)
    dht_device = adafruit_dht.DHT11(board.D4)
    temperature_c = dht_device.temperature
    humidity = dht_device.humidity

    # Soil moisture via MCP3008 channel 0 over SPI
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1350000
    adc_response = spi.xfer2([1, (8 + 0) << 4, 0])
    raw_value = ((adc_response[1] & 3) << 8) + adc_response[2]  # 0-1023
    spi.close()

    # MCP3008 reads 0 (fully wet) to 1023 (fully dry) on most modules --
    # invert + scale to a 0-100% "moisture" reading. Calibrate these two
    # numbers (dry_value, wet_value) for your specific sensor/soil.
    dry_value, wet_value = 900, 300
    moisture_pct = max(0, min(100, 100 * (dry_value - raw_value) / (dry_value - wet_value)))

    return {
        "soil_moisture": round(moisture_pct, 2),
        "temperature": round(temperature_c, 2) if temperature_c is not None else None,
        "humidity": round(humidity, 2) if humidity is not None else None,
    }


def read_simulated_sensors():
    """Fake but realistic readings, for testing without hardware."""
    return {
        "soil_moisture": round(random.uniform(25, 65), 2),
        "temperature": round(random.uniform(22, 34), 2),
        "humidity": round(random.uniform(45, 85), 2),
    }


def send_reading(server: str, api_key: str, farm_id: int, sensor_type: str, value: float, unit: str):
    try:
        resp = requests.post(
            f"{server}/api/sensor-reading",
            json={"farm_id": farm_id, "sensor_type": sensor_type, "value": value, "unit": unit},
            headers={"X-API-Key": api_key},
            timeout=10,
        )
        print(f"  {sensor_type}: {value}{unit} -> {resp.status_code}")
    except requests.RequestException as e:
        print(f"  {sensor_type}: FAILED to send ({e})")


def main():
    parser = argparse.ArgumentParser(description="Read sensors and push readings to the Flask server.")
    parser.add_argument("--farm-id", type=int, required=True, help="Farm_ID this Pi is monitoring")
    parser.add_argument("--server", type=str, required=True, help="e.g. http://192.168.1.20:5000")
    parser.add_argument("--api-key", type=str, default=DEFAULT_API_KEY)
    parser.add_argument("--simulate", action="store_true", help="Use fake readings instead of real hardware")
    parser.add_argument("--once", action="store_true", help="Send one reading and exit (for testing)")
    args = parser.parse_args()

    read_fn = read_simulated_sensors if args.simulate else read_real_sensors

    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Reading sensors...")
        try:
            readings = read_fn()
        except Exception as e:
            print(f"  Sensor read failed: {e}")
            if args.once:
                break
            time.sleep(INTERVAL_SECONDS)
            continue

        if readings.get("soil_moisture") is not None:
            send_reading(args.server, args.api_key, args.farm_id, "soil_moisture", readings["soil_moisture"], "%")
        if readings.get("temperature") is not None:
            send_reading(args.server, args.api_key, args.farm_id, "temperature", readings["temperature"], "C")
        if readings.get("humidity") is not None:
            send_reading(args.server, args.api_key, args.farm_id, "humidity", readings["humidity"], "%RH")

        if args.once:
            break
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
