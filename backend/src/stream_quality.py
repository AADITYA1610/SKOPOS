from collections import Counter


DEMO_RANGES = {
    "temperature": (-20.0, 60.0),
    "humidity": (0.0, 100.0),
}


def summarize_window(readings):
    """Inspect recent readings without modifying them."""

    record_count = len(readings)
    missing_counts = {field: 0 for field in DEMO_RANGES}
    out_of_range_counts = {field: 0 for field in DEMO_RANGES}
    issues = []

    identities = Counter(
        (record["sensor_id"], record["event_id"])
        for record in readings
    )

    duplicate_extra_records = sum(
        count - 1
        for count in identities.values()
        if count > 1
    )

    records_with_issues = 0

    for record in readings:
        record_issues = []

        for field, (lower, upper) in DEMO_RANGES.items():
            value = record.get(field)

            if value is None:
                missing_counts[field] += 1
                record_issues.append({
                    "type": "missing_measurement",
                    "field": field,
                    "value": None,
                })

            elif not lower <= value <= upper:
                out_of_range_counts[field] += 1
                record_issues.append({
                    "type": "outside_demo_range",
                    "field": field,
                    "value": value,
                    "expected_min": lower,
                    "expected_max": upper,
                })

        identity = (record["sensor_id"], record["event_id"])

        if identities[identity] > 1:
            record_issues.append({
                "type": "repeated_event_identity",
                "occurrences_in_window": identities[identity],
            })

        if record_issues:
            records_with_issues += 1
            issues.append({
                "event_id": record["event_id"],
                "sensor_id": record["sensor_id"],
                "received_at": record["received_at"],
                "flags": record_issues,
            })

    measurement_count = record_count * len(DEMO_RANGES)
    missing_total = sum(missing_counts.values())

    completeness_percentage = (
        round(
            100 * (measurement_count - missing_total) / measurement_count,
            2,
        )
        if measurement_count else None
    )

    return {
        "scope": "recent_arrival_window",
        "record_count": record_count,
        "missing_counts": missing_counts,
        "out_of_range_counts": out_of_range_counts,
        "duplicate_extra_records": duplicate_extra_records,
        "records_with_issues": records_with_issues,
        "completeness_percentage": completeness_percentage,
        "demo_ranges": {
            field: {"min": lower, "max": upper}
            for field, (lower, upper) in DEMO_RANGES.items()
        },
        "issues": issues,
    }