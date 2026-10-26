from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.activities.file_import import preview_activity_file
from app.activities.schemas import ActivityCreate, ActivityImportCommit, ActivityImportPreview
from app.activities.service import import_activity
from app.database.base import Base
from app.database.models import User


def test_preview_tcx_extracts_activity_metrics():
    tcx = b"""<?xml version="1.0" encoding="UTF-8"?>
    <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
      xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
      <Activities><Activity Sport="Biking">
        <Id>2026-10-27T17:00:00Z</Id>
        <Lap StartTime="2026-10-27T17:00:00Z">
          <TotalTimeSeconds>3900</TotalTimeSeconds><DistanceMeters>30000</DistanceMeters>
          <Track><Trackpoint><Time>2026-10-27T17:00:00Z</Time><DistanceMeters>0</DistanceMeters>
            <HeartRateBpm><Value>140</Value></HeartRateBpm><Extensions><ns3:TPX><ns3:Watts>200</ns3:Watts></ns3:TPX></Extensions>
          </Trackpoint><Trackpoint><Time>2026-10-27T18:05:00Z</Time><DistanceMeters>30000</DistanceMeters>
            <HeartRateBpm><Value>150</Value></HeartRateBpm><Extensions><ns3:TPX><ns3:Watts>220</ns3:Watts></ns3:TPX></Extensions>
          </Trackpoint></Track>
        </Lap>
      </Activity></Activities>
    </TrainingCenterDatabase>"""

    activity, fingerprint = preview_activity_file(tcx, "intervalos-umbral.tcx")

    assert activity["title"] == "intervalos umbral"
    assert activity["started_at"] == datetime(2026, 10, 27, 17, tzinfo=timezone.utc)
    assert activity["duration_minutes"] == pytest.approx(65)
    assert activity["distance_km"] == pytest.approx(30)
    assert activity["average_power"] == pytest.approx(210)
    assert activity["average_heart_rate"] == pytest.approx(145)
    assert len(fingerprint) == 64


def test_garmin_technical_filename_uses_friendly_activity_title():
    tcx = b"""<?xml version="1.0" encoding="UTF-8"?>
    <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
      <Activities><Activity Sport="Biking">
        <Id>2026-09-22T15:07:56Z</Id>
        <Lap StartTime="2026-09-22T15:07:56Z"><TotalTimeSeconds>3600</TotalTimeSeconds></Lap>
      </Activity></Activities>
    </TrainingCenterDatabase>"""

    activity, _ = preview_activity_file(tcx, "activity_24457923078.tcx")

    assert activity["title"] == "Actividad de ciclismo"


def test_preview_rejects_unknown_and_empty_files():
    with pytest.raises(ValueError, match="Formato no compatible"):
        preview_activity_file(b"content", "activity.csv")
    with pytest.raises(ValueError, match="vacío"):
        preview_activity_file(b"", "activity.tcx")


def test_preview_serializes_utc_timestamp_with_timezone():
    preview = ActivityImportPreview(
        filename="activity.tcx",
        fingerprint="a" * 64,
        duplicate=False,
        activity=ActivityCreate(
            title="Salida",
            started_at=datetime(2026, 10, 26, 15, 7, tzinfo=timezone.utc),
            duration_minutes=60,
        ),
    )

    assert preview.model_dump(mode="json")["activity"]["started_at"] == "2026-10-26T15:07:00Z"


def test_import_rejects_duplicate_file_for_same_user():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="import@example.com", display_name="Import rider")
        db.add(user)
        db.commit()

        payload = ActivityImportCommit(
            filename="activity.tcx",
            fingerprint="a" * 64,
            title="Salida importada",
            started_at=datetime(2026, 10, 27, 17, tzinfo=timezone.utc),
            sport="CYCLING",
            duration_minutes=65,
            distance_km=30,
            average_power=205,
            tss=68,
        )

        imported = import_activity(db, user.id, payload, "Europe/Madrid")

        assert imported.source == "FILE_IMPORT"
        assert imported.external_source_id == payload.fingerprint
        with pytest.raises(ValueError, match="ya se ha importado"):
            import_activity(db, user.id, payload, "Europe/Madrid")
