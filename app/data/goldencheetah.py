"""Import OpenData summaries and export observed weekly loads, without labels.

Dates are grouped in UTC. Missing weeks are unknown, never assumed rest.
The duration threshold is a configurable review heuristic, not a validity rule.
"""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


METRICS = {
    "duration_seconds": "workout_time",
    "average_power": "average_power",
    "normalized_power": "coggan_np",
    "intensity_factor": "coggan_if",
    "tss": "coggan_tss",
}

def signed_metric(value):
    """Lee una métrica finita que puede ser positiva o negativa."""
    if isinstance(value, list):
        value = value[0] if len(value) == 2 else None

    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return number

def metric(value):
    """Lee una métrica de GoldenCheetah que no puede ser negativa."""
    number = signed_metric(value)

    if number is None or number < 0:
        return None

    return number

def import_athlete(path, max_duration_hours=12):
    """Return normalized Bike records and an audit; fail on ambiguous identity."""
    if not math.isfinite(max_duration_hours) or max_duration_hours <= 0:
        raise ValueError("max_duration_hours must be positive and finite")
    path = Path(path)
    if path.is_dir():
        files = sorted(path.glob("*.json"))
        if len(files) != 1:
            raise ValueError(f"Expected one JSON summary in {path}")
        path = files[0]
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    athlete_id = str(data["ATHLETE"]["id"]).strip("{}")
    if not athlete_id:
        raise ValueError("Missing athlete identity")
    rides = data["RIDES"]
    audit = {"athlete_id": athlete_id, "source": str(path.resolve()),
             "source_records": len(rides), "skipped_non_bike": 0,
             "invalid_dates": 0, "duplicates": 0}
    records, seen = [], {}
    for ride in rides:
        if ride.get("sport") != "Bike":
            audit["skipped_non_bike"] += 1
            continue
        try:
            date = datetime.strptime(ride["date"], "%Y/%m/%d %H:%M:%S UTC")
        except (KeyError, TypeError, ValueError):
            audit["invalid_dates"] += 1
            continue
        if date in seen:
            if ride != seen[date]:
                raise ValueError(f"Conflicting activities at {date} for {athlete_id}")
            audit["duplicates"] += 1
            continue
        seen[date] = ride
        values = {name: metric(ride.get("METRICS", {}).get(key))
                  for name, key in METRICS.items()}
        duration = values["duration_seconds"]
        flags = []
        if duration is None or duration == 0:
            flags.append("invalid_duration")
        elif duration < 60 or duration > max_duration_hours * 3600:
            flags.append("duration_review")
        if values["tss"] is None:
            flags.append("missing_tss")
        if values["normalized_power"] is None:
            flags.append("missing_normalized_power")
        records.append({"athlete_id": athlete_id, "date_utc": date.isoformat() + "Z",
                        "week_start": (date.date() - timedelta(days=date.weekday())).isoformat(),
                        **values, "quality_flags": "|".join(flags)})
    audit["bike_records"] = len(records)
    audit["flag_counts"] = dict(Counter(flag for row in records
                                        for flag in row["quality_flags"].split("|") if flag))
    return sorted(records, key=lambda row: row["date_utc"]), audit

def weekly_table(records):
    """Include gap weeks and expose partial sums separately from usable totals.

    Edge weeks are marked conservatively: an activity export cannot establish
    that the full first or last calendar week was captured. Even interior
    coverage is coverage of recorded activities, not proof of complete logging.
    """
    athletes = defaultdict(list)
    for record in records:
        athletes[record["athlete_id"]].append(record)
    output = []
    for athlete_id, rows in sorted(athletes.items()):
        groups = defaultdict(list)
        for row in rows:
            groups[row["week_start"]].append(row)
        first, last = min(groups), max(groups)
        week = datetime.fromisoformat(first).date()
        while week.isoformat() <= last:
            key = week.isoformat()
            activities = groups[key]
            valid = [r for r in activities if r["tss"] is not None]
            review = any("duration" in r["quality_flags"] for r in activities)
            boundary = key in (first, last)
            observed = sum(r["tss"] for r in valid) if valid else None
            usable = bool(activities) and len(valid) == len(activities) and not review and not boundary
            output.append({"athlete_id": athlete_id, "week_start": key,
                "activity_count": len(activities),
                "training_days": len({r["date_utc"][:10] for r in activities}),
                "observed_duration_minutes": sum(r["duration_seconds"] / 60 for r in activities
                    if r["duration_seconds"] is not None) if activities else None,
                "tss_record_count": len(valid),
                "tss_coverage": len(valid) / len(activities) if activities else None,
                "observed_tss": observed, "weekly_tss": observed if usable else None,
                "no_records": not bool(activities), "duration_review": review,
                "boundary_week": boundary, "usable_load_week": usable})
            week += timedelta(days=7)
    return output

def write_csv(path, rows):
    if not rows:
        raise ValueError(f"No rows to export to {path}")
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path, help="Athlete folders or JSON summaries")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-duration-hours", type=float, default=12)
    args = parser.parse_args()
    records, audits, ids = [], [], set()
    for source in args.sources:
        rows, audit = import_athlete(source, args.max_duration_hours)
        if audit["athlete_id"] in ids:
            raise ValueError("Repeated athlete: merge exports explicitly before importing")
        ids.add(audit["athlete_id"])
        records.extend(rows)
        audits.append(audit)
    weeks = weekly_table(records)
    if not records:
        raise ValueError("No dated cycling records found")
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "activities.csv", records)
    write_csv(args.output / "weekly.csv", weeks)
    summary = {"athletes": audits, "activity_count": len(records), "week_count": len(weeks),
               "usable_load_weeks": sum(w["usable_load_week"] for w in weeks),
               "max_duration_hours": args.max_duration_hours, "timezone": "UTC",
               "labels_created": False}
    (args.output / "audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
