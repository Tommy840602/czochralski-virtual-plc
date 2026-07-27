from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class PlcRuntimeState(StrEnum):
    DISABLED = "DISABLED"
    DISCONNECTED = "DISCONNECTED"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    FAULT = "FAULT"


class SensorQuality(StrEnum):
    GOOD = "GOOD"
    UNCERTAIN = "UNCERTAIN"
    BAD = "BAD"


class PlcCommand(StrEnum):
    START = "start"
    STOP = "stop"
    RESET = "reset"


@dataclass(slots=True)
class PlantInputImage:
    temperature_c: float = 25.0
    pressure_torr: float = 760.0
    diameter_mm: float = 0.0
    pull_speed_mm_min: float = 0.0
    argon_flow_slm: float = 0.0
    crucible_position_mm: float = 0.0
    door_closed: bool = False
    emergency_stop_healthy: bool = False
    sensor_quality: SensorQuality = SensorQuality.BAD
    communication_online: bool = False
    plant_mode: str = "UNKNOWN"
    plant_phase: str = "UNKNOWN"
    plant_sequence: int = 0


@dataclass(slots=True)
class PlcOutputImage:
    heater_output_pct: float = 0.0
    pull_speed_mm_min: float = 0.0
    argon_valve_pct: float = 0.0
    vacuum_pump_pct: float = 0.0
    crucible_speed_rpm: float = 0.0
    seed_rotation_rpm: float = 0.0
    cooling_output_pct: float = 0.0
    interlock_permit: bool = False
    emergency_stop: bool = False


@dataclass(frozen=True, slots=True)
class InterlockStatus:
    key: str
    label: str
    healthy: bool
    blocking: bool = True


@dataclass(slots=True)
class PlcRuntimeSnapshot:
    enabled: bool
    connected: bool
    state: PlcRuntimeState
    requested_run: bool
    cycle_count: int
    scan_time_ms: float
    last_scan_at: str | None
    last_error: str | None
    inputs: PlantInputImage
    outputs: PlcOutputImage
    interlocks: list[InterlockStatus] = field(default_factory=list)
    alarms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["state"] = self.state.value
        result["inputs"]["sensor_quality"] = self.inputs.sensor_quality.value
        return result


def utc_now() -> str:
    return datetime.now(UTC).isoformat()
