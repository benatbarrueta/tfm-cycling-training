from datetime import datetime, timedelta, timezone

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
          <Extensions><ns3:LX><ns3:NormalizedPower>210</ns3:NormalizedPower></ns3:LX></Extensions>
          <Track><Trackpoint><Time>2026-10-27T17:00:00Z</Time><DistanceMeters>0</DistanceMeters>
            <HeartRateBpm><Value>140</Value></HeartRateBpm><Extensions><ns3:TPX><ns3:Watts>200</ns3:Watts></ns3:TPX></Extensions>
          </Trackpoint><Trackpoint><Time>2026-10-27T18:05:00Z</Time><DistanceMeters>30000</DistanceMeters>
            <HeartRateBpm><Value>150</Value></HeartRateBpm><Extensions><ns3:TPX><ns3:Watts>220</ns3:Watts></ns3:TPX></Extensions>
          </Trackpoint></Track>
        </Lap>
      </Activity></Activities>
    </TrainingCenterDatabase>"""

    activity, fingerprint, warnings = preview_activity_file(tcx, "intervalos-umbral.tcx", ftp=250)

    assert activity["title"] == "intervalos umbral"
    assert activity["started_at"] == datetime(2026, 10, 27, 17, tzinfo=timezone.utc)
    assert activity["duration_minutes"] == pytest.approx(65)
    assert activity["distance_km"] == pytest.approx(30)
    assert activity["average_power"] == pytest.approx(210)
    assert activity["normalized_power"] == pytest.approx(210)
    assert activity["intensity_factor"] == pytest.approx(0.84)
    assert activity["tss"] == pytest.approx(76.44)
    assert activity["average_heart_rate"] == pytest.approx(145)
    assert len(fingerprint) == 64
    assert warnings == {
        "aerobic_decoupling": (
            "Desacoplamiento no disponible: el tramo continuo más largo con "
            "potencia y frecuencia cardiaca dura 0.0 min y se necesitan al "
            "menos 20 min."
        )
    }


def test_preview_tcx_calculates_decoupling_from_power_and_heart_rate():
    points = []
    started_at = datetime(2026, 10, 27, 17, tzinfo=timezone.utc)
    for second in range(1201):
        heart_rate = 140 if second <= 600 else 150
        timestamp = (started_at + timedelta(seconds=second)).isoformat().replace("+00:00", "Z")
        points.append(
            f"""<Trackpoint><Time>{timestamp}</Time>
            <HeartRateBpm><Value>{heart_rate}</Value></HeartRateBpm>
            <Extensions><ns3:TPX><ns3:Watts>200</ns3:Watts></ns3:TPX></Extensions></Trackpoint>"""
        )
    tcx = f"""<?xml version="1.0" encoding="UTF-8"?>
    <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
      xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
      <Activities><Activity Sport="Biking"><Id>2026-10-27T17:00:00Z</Id>
      <Lap><TotalTimeSeconds>1200</TotalTimeSeconds><Track>{''.join(points)}</Track></Lap>
      </Activity></Activities></TrainingCenterDatabase>""".encode()

    activity, _, warnings = preview_activity_file(tcx, "response.tcx", ftp=250)

    assert activity["aerobic_decoupling"] is not None
    assert activity["aerobic_decoupling"] > 0
    assert activity["aerobic_decoupling"] == round(activity["aerobic_decoupling"], 2)
    assert warnings == {
        "distance_km": "El archivo no contiene una distancia válida."
    }


def test_garmin_technical_filename_uses_friendly_activity_title():
    tcx = b"""<?xml version="1.0" encoding="UTF-8"?>
    <TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
      <Activities><Activity Sport="Biking">
        <Id>2026-09-22T15:07:56Z</Id>
        <Lap StartTime="2026-09-22T15:07:56Z"><TotalTimeSeconds>3600</TotalTimeSeconds></Lap>
      </Activity></Activities>
    </TrainingCenterDatabase>"""

    activity, _, warnings = preview_activity_file(tcx, "activity_24457923078.tcx")

    assert activity["title"] == "Actividad de ciclismo"
    assert warnings["distance_km"] == "El archivo no contiene una distancia válida."
    assert warnings["average_power"] == "El archivo no contiene datos de potencia."
    assert warnings["average_heart_rate"] == (
        "El archivo no contiene datos de frecuencia cardiaca."
    )
    assert "30 segundos" in warnings["normalized_power"]
    assert "potencia normalizada" in warnings["intensity_factor"]
    assert "potencia normalizada" in warnings["tss"]
    assert "simultáneas" in warnings["aerobic_decoupling"]


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
