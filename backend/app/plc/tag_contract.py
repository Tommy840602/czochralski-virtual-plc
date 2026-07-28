from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class TagDirection(StrEnum):
    PLANT_TO_PLC = "PLANT_TO_PLC"
    PLC_TO_PLANT = "PLC_TO_PLANT"
    PLANT_STATUS = "PLANT_STATUS"


@dataclass(frozen=True, slots=True)
class PlcTag:
    node_id: str
    field: str
    direction: TagDirection
    data_type: str
    unit: str | None
    writable: bool

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["direction"] = self.direction.value
        return result


INPUT_TAGS: tuple[PlcTag, ...] = (
    PlcTag("Plant.TemperaturePV", "temperature_c", TagDirection.PLANT_TO_PLC, "Double", "degC", False),
    PlcTag("Plant.PressurePV", "pressure_torr", TagDirection.PLANT_TO_PLC, "Double", "torr", False),
    PlcTag("Plant.DiameterPV", "diameter_mm", TagDirection.PLANT_TO_PLC, "Double", "mm", False),
    PlcTag("Plant.PullSpeedPV", "pull_speed_mm_min", TagDirection.PLANT_TO_PLC, "Double", "mm/min", False),
    PlcTag("Plant.ArgonFlowPV", "argon_flow_slm", TagDirection.PLANT_TO_PLC, "Double", "slm", False),
    PlcTag(
        "Plant.CruciblePositionPV",
        "crucible_position_mm",
        TagDirection.PLANT_TO_PLC,
        "Double",
        "mm",
        False,
    ),
    PlcTag("Plant.DoorClosed", "door_closed", TagDirection.PLANT_TO_PLC, "Boolean", None, False),
    PlcTag(
        "Plant.EStopHealthy",
        "emergency_stop_healthy",
        TagDirection.PLANT_TO_PLC,
        "Boolean",
        None,
        False,
    ),
)

STATUS_TAGS: tuple[PlcTag, ...] = (
    PlcTag("Status.Mode", "plant_mode", TagDirection.PLANT_STATUS, "String", None, False),
    PlcTag("Status.ProcessPhase", "plant_phase", TagDirection.PLANT_STATUS, "String", None, False),
    PlcTag("Status.CycleId", "cycle_id", TagDirection.PLANT_STATUS, "String", None, False),
    PlcTag("Status.IngotId", "ingot_id", TagDirection.PLANT_STATUS, "String", None, False),
    PlcTag(
        "Status.CycleOutcome",
        "cycle_outcome",
        TagDirection.PLANT_STATUS,
        "String",
        None,
        False,
    ),
    PlcTag(
        "Status.SensorQuality",
        "sensor_quality",
        TagDirection.PLANT_STATUS,
        "String",
        None,
        False,
    ),
    PlcTag(
        "Status.CommunicationOnline",
        "communication_online",
        TagDirection.PLANT_STATUS,
        "Boolean",
        None,
        False,
    ),
    PlcTag("Status.Sequence", "plant_sequence", TagDirection.PLANT_STATUS, "UInt64", None, False),
)

OUTPUT_TAGS: tuple[PlcTag, ...] = (
    PlcTag("PLC.HeaterOutput", "heater_output_pct", TagDirection.PLC_TO_PLANT, "Double", "%", True),
    PlcTag(
        "PLC.PullSpeedOutput",
        "pull_speed_mm_min",
        TagDirection.PLC_TO_PLANT,
        "Double",
        "mm/min",
        True,
    ),
    PlcTag("PLC.ArgonValveOutput", "argon_valve_pct", TagDirection.PLC_TO_PLANT, "Double", "%", True),
    PlcTag("PLC.VacuumPumpOutput", "vacuum_pump_pct", TagDirection.PLC_TO_PLANT, "Double", "%", True),
    PlcTag(
        "PLC.CrucibleSpeedOutput",
        "crucible_speed_rpm",
        TagDirection.PLC_TO_PLANT,
        "Double",
        "rpm",
        True,
    ),
    PlcTag(
        "PLC.SeedRotationOutput",
        "seed_rotation_rpm",
        TagDirection.PLC_TO_PLANT,
        "Double",
        "rpm",
        True,
    ),
    PlcTag("PLC.CoolingOutput", "cooling_output_pct", TagDirection.PLC_TO_PLANT, "Double", "%", True),
    PlcTag("PLC.InterlockPermit", "interlock_permit", TagDirection.PLC_TO_PLANT, "Boolean", None, True),
    PlcTag("PLC.EmergencyStop", "emergency_stop", TagDirection.PLC_TO_PLANT, "Boolean", None, True),
)

ALL_TAGS = INPUT_TAGS + STATUS_TAGS + OUTPUT_TAGS


def tag_contract() -> dict[str, object]:
    return {
        "version": "2.0.0",
        "namespace": "urn:tommy-huang:cz-plant-simulator",
        "tags": [tag.to_dict() for tag in ALL_TAGS],
    }
