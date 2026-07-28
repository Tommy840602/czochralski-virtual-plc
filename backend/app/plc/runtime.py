from __future__ import annotations

import asyncio
from contextlib import suppress
from time import perf_counter

from app.core.config import Settings
from app.plc.adapter import OpcUaPlantAdapter, PlantAdapter
from app.plc.models import (
    InterlockStatus,
    PlantInputImage,
    PlcCommand,
    PlcOutputImage,
    PlcRuntimeSnapshot,
    PlcRuntimeState,
    SensorQuality,
    utc_now,
)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class VirtualPlcRuntime:
    def __init__(self, settings: Settings, adapter: PlantAdapter | None = None) -> None:
        self.settings = settings
        self.enabled = settings.runtime_enabled
        self.adapter = adapter
        self.connected = False
        self.requested_run = False
        self.inputs = PlantInputImage()
        self.outputs = PlcOutputImage()
        self.cycle_count = 0
        self.scan_time_ms = 0.0
        self.last_scan_at: str | None = None
        self.last_error: str | None = None
        self._task: asyncio.Task[None] | None = None
        self._command_lock = asyncio.Lock()
        self._scan_lock = asyncio.Lock()

    async def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        if self.adapter is None:
            self.adapter = OpcUaPlantAdapter(
                endpoint=self.settings.plant_opcua_endpoint,
                namespace_uri=self.settings.plant_opcua_namespace,
                api_url=self.settings.plant_api_url,
            )
        self._task = asyncio.create_task(self._run(), name="virtual-plc-scan")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self.adapter is not None and self.adapter.connected:
            with suppress(Exception):
                await self.adapter.write_outputs(
                    PlcOutputImage(
                        interlock_permit=False,
                        emergency_stop=True,
                    )
                )
            with suppress(Exception):
                await self.adapter.disconnect()
        self.requested_run = False
        self.outputs = PlcOutputImage(
            interlock_permit=False,
            emergency_stop=True,
        )
        self.connected = False

    async def scan_once(self) -> PlcRuntimeSnapshot:
        async with self._scan_lock:
            started_at = perf_counter()
            if not self.enabled:
                return self.snapshot()
            if self.adapter is None:
                raise RuntimeError("PLC runtime adapter is not configured")

            try:
                if not self.adapter.connected:
                    await self.adapter.connect()
                self.connected = True
                self.inputs = await self.adapter.read_inputs()
                if self.inputs.cycle_outcome in {"COMPLETED", "ABORTED"}:
                    self.requested_run = False
                interlocks = self._interlocks()
                tripped = any(
                    item.blocking and not item.healthy for item in interlocks
                )
                if tripped:
                    # Interlock trip is stop-dominant: recovery must never
                    # restart equipment without another explicit START.
                    self.requested_run = False
                    self.outputs = self._safe_outputs(tripped=True)
                else:
                    self.outputs = self._control_outputs()
                await self.adapter.write_outputs(self.outputs)
                self.cycle_count += 1
                self.last_scan_at = utc_now()
                self.last_error = None
            except Exception as exc:
                self.connected = False
                self.outputs = PlcOutputImage(
                    interlock_permit=False,
                    emergency_stop=True,
                )
                self.last_error = f"{type(exc).__name__}: {exc}"
                if self.adapter.connected:
                    with suppress(Exception):
                        await self.adapter.disconnect()
            finally:
                self.scan_time_ms = round(
                    (perf_counter() - started_at) * 1000.0,
                    3,
                )
            return self.snapshot()

    async def command(self, command: PlcCommand) -> PlcRuntimeSnapshot:
        if not self.enabled:
            raise ValueError("Virtual PLC runtime is disabled")
        if self.adapter is None:
            raise ValueError("Plant Simulator adapter is not configured")

        async with self._command_lock:
            if not self.adapter.connected:
                await self.adapter.connect()
                self.connected = True
                self.inputs = await self.adapter.read_inputs()
            if command is PlcCommand.START:
                blocking = [
                    item.label
                    for item in self._interlocks()
                    if item.blocking and not item.healthy
                ]
                if blocking:
                    raise ValueError("Start blocked by: " + ", ".join(blocking))
                await self.adapter.command("start")
                self.requested_run = True
            elif command is PlcCommand.STOP:
                await self.adapter.command("stop")
                self.requested_run = False
            elif command is PlcCommand.RESET:
                await self.adapter.command("reset")
                self.requested_run = False
                self.outputs = PlcOutputImage()
            return await self.scan_once()

    def snapshot(self) -> PlcRuntimeSnapshot:
        interlocks = self._interlocks()
        tripped = any(item.blocking and not item.healthy for item in interlocks)
        if not self.enabled:
            state = PlcRuntimeState.DISABLED
        elif not self.connected:
            state = PlcRuntimeState.DISCONNECTED
        elif tripped:
            state = PlcRuntimeState.FAULT
        elif self.requested_run and self.inputs.plant_mode == "RUNNING":
            state = PlcRuntimeState.RUNNING
        else:
            state = PlcRuntimeState.STOPPED
        return PlcRuntimeSnapshot(
            enabled=self.enabled,
            connected=self.connected,
            state=state,
            requested_run=self.requested_run,
            cycle_count=self.cycle_count,
            scan_time_ms=self.scan_time_ms,
            last_scan_at=self.last_scan_at,
            last_error=self.last_error,
            inputs=self.inputs,
            outputs=self.outputs,
            interlocks=interlocks,
            alarms=self._alarms(),
        )

    def _interlocks(self) -> list[InterlockStatus]:
        return [
            InterlockStatus("opcua", "Plant OPC UA connected", self.connected),
            InterlockStatus(
                "communication",
                "Plant communication online",
                self.inputs.communication_online,
            ),
            InterlockStatus(
                "quality",
                "Sensor quality acceptable",
                self.inputs.sensor_quality in {SensorQuality.GOOD, SensorQuality.UNCERTAIN},
            ),
            InterlockStatus("door", "Safety door closed", self.inputs.door_closed),
            InterlockStatus(
                "estop",
                "Emergency-stop circuit healthy",
                self.inputs.emergency_stop_healthy,
            ),
        ]

    def _alarms(self) -> list[str]:
        alarms: list[str] = []
        if self.last_error:
            alarms.append(self.last_error)
        if self.inputs.sensor_quality is SensorQuality.UNCERTAIN:
            alarms.append("Sensor quality is UNCERTAIN")
        if self.inputs.sensor_quality is SensorQuality.BAD:
            alarms.append("Sensor quality is BAD")
        if self.requested_run and self.inputs.temperature_c > 1600.0:
            alarms.append("Hot-zone temperature high")
        if self.requested_run and self.inputs.pressure_torr > 250.0:
            alarms.append("Chamber pressure has not reached process range")
        if self.inputs.plant_phase == "BODY" and abs(self.inputs.diameter_mm - 200.0) > 12.0:
            alarms.append("BODY diameter deviation exceeds 12 mm")
        return alarms

    def _safe_outputs(self, tripped: bool) -> PlcOutputImage:
        return PlcOutputImage(
            interlock_permit=False,
            emergency_stop=tripped,
        )

    def _control_outputs(self) -> PlcOutputImage:
        if not self.requested_run:
            return PlcOutputImage(interlock_permit=True)

        phase = self.inputs.plant_phase
        base = {
            "MELT": PlcOutputImage(
                heater_output_pct=84.0,
                argon_valve_pct=60.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=8.0,
                interlock_permit=True,
            ),
            "STABILIZE": PlcOutputImage(
                heater_output_pct=82.0,
                argon_valve_pct=60.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=8.0,
                interlock_permit=True,
            ),
            "SEED": PlcOutputImage(
                heater_output_pct=82.0,
                pull_speed_mm_min=0.4,
                argon_valve_pct=60.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=8.0,
                seed_rotation_rpm=12.0,
                interlock_permit=True,
            ),
            "NECK": PlcOutputImage(
                heater_output_pct=80.0,
                pull_speed_mm_min=2.5,
                argon_valve_pct=60.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=8.0,
                seed_rotation_rpm=15.0,
                interlock_permit=True,
            ),
            "CROWN": PlcOutputImage(
                heater_output_pct=81.0,
                pull_speed_mm_min=1.2,
                argon_valve_pct=60.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=8.0,
                seed_rotation_rpm=12.0,
                interlock_permit=True,
            ),
            "TAIL": PlcOutputImage(
                heater_output_pct=70.0,
                pull_speed_mm_min=1.5,
                argon_valve_pct=45.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=6.0,
                seed_rotation_rpm=8.0,
                cooling_output_pct=20.0,
                interlock_permit=True,
            ),
        }
        if phase == "BODY":
            temperature_error = 1420.0 - self.inputs.temperature_c
            diameter_error = 200.0 - self.inputs.diameter_mm
            heater = _clamp(82.0 + temperature_error * 0.035, 65.0, 95.0)
            pull_speed = _clamp(1.1 - diameter_error * 0.004, 0.6, 1.8)
            return PlcOutputImage(
                heater_output_pct=heater,
                pull_speed_mm_min=pull_speed,
                argon_valve_pct=60.0,
                vacuum_pump_pct=85.0,
                crucible_speed_rpm=8.0,
                seed_rotation_rpm=12.0,
                interlock_permit=True,
            )
        return base.get(phase, PlcOutputImage(interlock_permit=True))

    async def _run(self) -> None:
        while True:
            await self.scan_once()
            await asyncio.sleep(self.settings.scan_interval_seconds)
