from app.plc.dcs_contract import (
    DCS_TELEMETRY_SCHEMA,
    REALTIME_MONITORING_INTERVAL_MS,
    dcs_snapshot,
)
from app.main import app
from app.plc.models import (
    InterlockStatus,
    PlantInputImage,
    PlcOutputImage,
    PlcRuntimeSnapshot,
    PlcRuntimeState,
    SensorQuality,
)


def test_maps_authoritative_plc_image_to_dcs_contract():
    snapshot = PlcRuntimeSnapshot(
        enabled=True,
        connected=True,
        state=PlcRuntimeState.RUNNING,
        requested_run=True,
        cycle_count=42,
        scan_time_ms=3.5,
        last_scan_at="2026-07-27T00:00:00+00:00",
        last_error=None,
        inputs=PlantInputImage(
            temperature_c=1418.0,
            pressure_torr=21.0,
            diameter_mm=199.5,
            pull_speed_mm_min=1.1,
            argon_flow_slm=60.0,
            crucible_position_mm=80.0,
            door_closed=True,
            emergency_stop_healthy=True,
            sensor_quality=SensorQuality.GOOD,
            communication_online=True,
            plant_mode="RUNNING",
            plant_phase="BODY",
            cycle_id="cycle-20260727-001",
            ingot_id="CZ01-20260727-001",
            cycle_outcome="IN_PROGRESS",
            plant_sequence=7,
        ),
        outputs=PlcOutputImage(
            heater_output_pct=82.1,
            pull_speed_mm_min=1.08,
            argon_valve_pct=60.0,
            vacuum_pump_pct=85.0,
            crucible_speed_rpm=8.0,
            seed_rotation_rpm=12.0,
            interlock_permit=True,
        ),
        interlocks=[InterlockStatus("communication", "Communication", True)],
        alarms=[],
    )

    payload = dcs_snapshot(snapshot)

    assert payload["schema"] == DCS_TELEMETRY_SCHEMA
    assert payload["source"] == "CZ_VIRTUAL_PLC"
    assert payload["sequence"] == 42
    assert payload["healthy"] is True
    telemetry = payload["telemetry"]
    assert telemetry["diameterMean"] == 199.5
    assert telemetry["heaterTemp"] == 1418.0
    assert telemetry["heaterPower"] == 82.1
    assert telemetry["seedLiftSp"] == 1.08
    assert telemetry["simulationSource"] == "CZ_VIRTUAL_PLC"
    assert telemetry["plcAuthoritative"] is True
    assert telemetry["plcInterlockPermit"] is True
    assert telemetry["cycleId"] == "cycle-20260727-001"
    assert telemetry["ingot"] == "CZ01-20260727-001"
    assert telemetry["cycleOutcome"] == "IN_PROGRESS"
    assert telemetry["monitoringIntervalMs"] == REALTIME_MONITORING_INTERVAL_MS == 1_000


def test_internal_dcs_snapshot_is_versioned_and_not_cached():
    from fastapi.testclient import TestClient

    response = TestClient(app).get("/internal/dcs/v1/snapshot")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["schema"] == DCS_TELEMETRY_SCHEMA
    assert response.json()["source"] == "CZ_VIRTUAL_PLC"
