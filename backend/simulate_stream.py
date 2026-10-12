import time
from datetime import datetime, timezone

import httpx


BASE_URL = "http://127.0.0.1:8000"
INTERVAL_SECONDS = 2

# Fixed examples make the presentation repeatable.
DEMO_READINGS = [
    (25.4, 62.0),
    (25.8, None),   # Missing humidity
    (85.0, 63.0),   # Temperature outside demo range
    (26.1, 120.0),  # Humidity outside valid percentage range
    (None, 64.0),   # Missing temperature
    (26.0, 61.0),
    (25.7, 60.0),
    (25.9, 62.0),
    (26.2, 63.0),
    (26.4, 64.0),
    (26.1, 62.0),
    (25.8, 61.0),
]


def send_reading(client, session_id, reading):
    response = client.post(
        f"/streams/sessions/{session_id}/readings",
        json=reading,
    )
    response.raise_for_status()
    result = response.json()

    print(
        f"Sent {reading['event_id']} | "
        f"temperature={reading['temperature']} | "
        f"humidity={reading['humidity']} | "
        f"total={result['total_received']} | "
        f"window={result['window_count']}"
    )


def main():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        response = client.post(
            "/streams/sessions",
            json={
                "name": "Skopos simulated sensor demo",
                "source_type": "simulated",
                "window_size": 10,
            },
        )
        response.raise_for_status()
        session = response.json()
        session_id = session["session_id"]

        print(f"\nSession ID: {session_id}")
        print(f"Monitor URL: {BASE_URL}/streams/sessions/{session_id}")
        print("Sending readings every two seconds. Ctrl+C stops the demo.\n")

        for index, (temperature, humidity) in enumerate(
            DEMO_READINGS, start=1
        ):
            reading = {
                "event_id": f"reading-{index:03d}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensor_id": "sensor-A",
                "temperature": temperature,
                "humidity": humidity,
            }

            send_reading(client, session_id, reading)
            time.sleep(INTERVAL_SECONDS)

            if index == 3:
                print("Repeating the previous event to test duplicates.")
                send_reading(client, session_id, reading)
                time.sleep(INTERVAL_SECONDS)

        response = client.get(f"/streams/sessions/{session_id}")
        response.raise_for_status()
        result = response.json()
        quality = result["quality_summary"]

        print("\nDemo complete.")
        print(f"Total received: {result['total_received']}")
        print(f"Recent window count: {result['window_count']}")
        print(f"Missing measurements: {quality['missing_counts']}")
        print(f"Range violations: {quality['out_of_range_counts']}")
        print(f"Extra duplicate records: {quality['duplicate_extra_records']}")
        print(f"Completeness: {quality['completeness_percentage']}%")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
    except httpx.HTTPStatusError as exc:
        print(f"\nAPI error: {exc.response.status_code}")
        print(exc.response.text)
    except httpx.RequestError as exc:
        print(f"\nCould not complete the API request: {exc}")
        print("Check that the backend is running on port 8000.")