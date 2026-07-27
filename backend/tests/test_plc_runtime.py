import asyncio
from dataclasses import replace

import pytest

from app.core.config import Settings
from app.plc.models import (
    PlantInputImage,
    PlcCommand,
    PlcOutputImage,
    PlcRuntimeState,
    SensorQuality,
)
from app.plc.runtime import VirtualPlcRuntime
from app.plc.tag_contract import ALL_TAGS, OUTPUT_TAGS, tag_contract


class FakePlantAdapter:
    def __init__(self, inputs: PlantInputImage) -> None:
        self.connected = False
        self.inputs = inputs
        self.writes: list[PlcOutputImage] = []
        self.commands: list[str] = []

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def read_inputs(self) -> PlantInputImage:
        return replace(self.inputs)

    async def write_outputs(self, outputs: PlcOutputImage) -> None:
        self.writes.append(replace(outputs))

    async def command(self, command: str) -> None:
        self.commands.append(command)


def healthy_inputs(**overrides) -> PlantInputImage:
    values = {
        "temperature_c": 1420.0,
        "pressure_torr": 20.0,
        "diameter_mm": 200.0,
        "door_closed": True,
        "emergency_stop_healthy": True,
        "sensor_quality": SensorQuality.GOOD,
        "communication_online": True,
        "plant_mode": "RUNNING",
        "plant_phase": "BODY",
        "plant_sequence": 42,
    }
    values.update(overrides)
    return PlantInputImage(**values)


def runtime_settings() -> Settings:
    return Settings(
        _env_file=None,
        runtime_enabled=True,
        scan_interval_seconds=0.2,
    )


def test_scan_builds_input_image_and_safe_stopped_output():
    adapter = FakePlantAdapter(healthy_inputs())
    runtime = VirtualPlcRuntime(runtime_settings(), adapter)

    snapshot = asyncio.run(runtime.scan_once())

    assert snapshot.state is PlcRuntimeState.STOPPED
    assert snapshot.connected is True
    assert snapshot.cycle_count == 1
    assert snapshot.inputs.plant_sequence == 42
    assert adapter.writes[-1].interlock_permit is True
    assert adapter.writes[-1].heater_output_pct == 0.0


def test_start_command_runs_body_control_and_writes_outputs():
    adapter = FakePlantAdapter(
        healthy_inputs(temperature_c=1400.0, diameter_mm=190.0)
    )
    runtime = VirtualPlcRuntime(runtime_settings(), adapter)

    snapshot = asyncio.run(runtime.command(PlcCommand.START))

    assert adapter.commands == ["start"]
    assert snapshot.state is PlcRuntimeState.RUNNING
    assert snapshot.outputs.interlock_permit is True
    assert snapshot.outputs.heater_output_pct == pytest.approx(82.7)
    assert snapshot.outputs.pull_speed_mm_min == pytest.approx(1.06)


def test_bad_sensor_quality_trips_runtime_and_forces_safe_outputs():
    adapter = FakePlantAdapter(
        healthy_inputs(sensor_quality=SensorQuality.BAD)
    )
    runtime = VirtualPlcRuntime(runtime_settings(), adapter)
    runtime.requested_run = True

    snapshot = asyncio.run(runtime.scan_once())

    assert snapshot.state is PlcRuntimeState.FAULT
    assert snapshot.outputs.interlock_permit is False
    assert snapshot.outputs.emergency_stop is True
    assert snapshot.outputs.heater_output_pct == 0.0
    assert snapshot.requested_run is False
    assert "Sensor quality is BAD" in snapshot.alarms


def test_start_is_rejected_when_safety_door_is_open():
    adapter = FakePlantAdapter(healthy_inputs(door_closed=False))
    runtime = VirtualPlcRuntime(runtime_settings(), adapter)

    with pytest.raises(ValueError, match="Safety door closed"):
        asyncio.run(runtime.command(PlcCommand.START))

    assert adapter.commands == []


def test_runtime_shutdown_writes_safe_outputs_before_disconnect():
    adapter = FakePlantAdapter(healthy_inputs())
    runtime = VirtualPlcRuntime(runtime_settings(), adapter)

    async def exercise_shutdown():
        await runtime.scan_once()
        runtime.requested_run = True
        await runtime.stop()

    asyncio.run(exercise_shutdown())

    assert adapter.connected is False
    assert adapter.writes[-1].interlock_permit is False
    assert adapter.writes[-1].emergency_stop is True
    assert runtime.requested_run is False


def test_tag_contract_has_unique_nodes_and_only_outputs_are_writable():
    contract = tag_contract()
    node_ids = [tag.node_id for tag in ALL_TAGS]

    assert contract["version"] == "1.0.0"
    assert len(node_ids) == len(set(node_ids))
    assert all(tag.writable for tag in OUTPUT_TAGS)
    assert all(not tag.writable for tag in ALL_TAGS if tag not in OUTPUT_TAGS)
