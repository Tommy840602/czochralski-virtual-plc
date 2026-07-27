from __future__ import annotations

from app.plc.models import PlcRuntimeSnapshot, utc_now

DCS_TELEMETRY_SCHEMA = "cz.plc.dcs.telemetry.v1"
DCS_SOURCE = "CZ_VIRTUAL_PLC"
# PLC control scan remains 200 ms. Only the cross-system monitoring cadence is 1 Hz.
REALTIME_MONITORING_INTERVAL_MS = 1_000


def dcs_snapshot(snapshot: PlcRuntimeSnapshot) -> dict[str, object]:
    """Map the authoritative PLC image to the DCS Sparkplug telemetry contract."""
    inputs = snapshot.inputs
    outputs = snapshot.outputs
    observed_at = snapshot.last_scan_at or utc_now()
    healthy = (
        snapshot.enabled
        and snapshot.connected
        and snapshot.last_error is None
        and all(item.healthy for item in snapshot.interlocks if item.blocking)
    )

    telemetry = {
        "t": observed_at,
        "mode": snapshot.state.value,
        "sop": inputs.plant_phase,
        "diameter": inputs.diameter_mm,
        "diameterMean": inputs.diameter_mm,
        "diameterTarget": 200.0,
        "growthRateMean": inputs.pull_speed_mm_min,
        "seedLift": inputs.pull_speed_mm_min,
        "seedLiftSp": outputs.pull_speed_mm_min,
        "seedLiftTarget": outputs.pull_speed_mm_min,
        "heaterPower": outputs.heater_output_pct,
        "heaterTemp": inputs.temperature_c,
        "heaterTempTarget": 1420.0,
        "bodyLength": 0.0,
        "neckLength": 0.0,
        "crucibleLiftRatio": 0.0,
        "crucibleLift": inputs.crucible_position_mm,
        "crucibleRotationSp": outputs.crucible_speed_rpm,
        "cruciblePosition": inputs.crucible_position_mm,
        "cruciblePositionSp": 80.0,
        "throttleValve": outputs.vacuum_pump_pct,
        "residualWeight": 0.0,
        "seedRotationSp": outputs.seed_rotation_rpm,
        "argonFlow": inputs.argon_flow_slm,
        "argonFlowSp": 60.0,
        "chamberPressure": inputs.pressure_torr,
        "chamberPressureSp": 20.0,
        "ingot": "CZ01-PLC-LIVE",
        "event": inputs.plant_sequence % (2**31),
        "simulationSource": DCS_SOURCE,
        "simulationRandomized": False,
        "simulationControllerCount": 1,
        "simulationControlStrategy": "PLC_LOCAL_CONTROL",
        "simulationBaselineAuthority": False,
        "plcRuntimeState": snapshot.state.value,
        "plcConnected": snapshot.connected,
        "plcCycleCount": snapshot.cycle_count,
        "plcScanTimeMs": snapshot.scan_time_ms,
        "plcInterlockPermit": outputs.interlock_permit,
        "plcEmergencyStop": outputs.emergency_stop,
        "plcAlarmCount": len(snapshot.alarms),
        "plcDataContract": DCS_TELEMETRY_SCHEMA,
        "plcAuthoritative": True,
        "monitoringIntervalMs": REALTIME_MONITORING_INTERVAL_MS,
        "plcArgonValveOutput": outputs.argon_valve_pct,
        "plcCoolingOutput": outputs.cooling_output_pct,
    }

    return {
        "schema": DCS_TELEMETRY_SCHEMA,
        "source": DCS_SOURCE,
        "observedAt": observed_at,
        "sequence": snapshot.cycle_count,
        "healthy": healthy,
        "telemetry": telemetry,
    }
