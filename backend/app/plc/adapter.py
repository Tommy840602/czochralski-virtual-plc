from __future__ import annotations

import asyncio
import json
from typing import Protocol
from urllib.request import Request, urlopen

from asyncua import Client, ua

from app.plc.models import PlantInputImage, PlcOutputImage, SensorQuality
from app.plc.tag_contract import INPUT_TAGS, OUTPUT_TAGS, STATUS_TAGS


class PlantAdapter(Protocol):
    connected: bool

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def read_inputs(self) -> PlantInputImage: ...

    async def write_outputs(self, outputs: PlcOutputImage) -> None: ...

    async def command(self, command: str) -> None: ...


class OpcUaPlantAdapter:
    def __init__(
        self,
        endpoint: str,
        namespace_uri: str,
        api_url: str,
        *,
        request_timeout_seconds: float = 3.0,
    ) -> None:
        self.endpoint = endpoint
        self.namespace_uri = namespace_uri
        self.api_url = api_url.rstrip("/")
        self.request_timeout_seconds = request_timeout_seconds
        self.connected = False
        self._client: Client | None = None
        self._input_nodes: dict[str, object] = {}
        self._output_nodes: dict[str, object] = {}

    async def connect(self) -> None:
        if self.connected:
            return
        client = Client(self.endpoint)
        await client.connect()
        namespace_index = await client.get_namespace_index(self.namespace_uri)
        self._input_nodes = {
            tag.field: client.get_node(ua.NodeId(tag.node_id, namespace_index))
            for tag in INPUT_TAGS + STATUS_TAGS
        }
        self._output_nodes = {
            tag.field: client.get_node(ua.NodeId(tag.node_id, namespace_index))
            for tag in OUTPUT_TAGS
        }
        self._client = client
        self.connected = True

    async def disconnect(self) -> None:
        client, self._client = self._client, None
        self.connected = False
        self._input_nodes.clear()
        self._output_nodes.clear()
        if client is not None:
            await client.disconnect()

    async def read_inputs(self) -> PlantInputImage:
        if not self.connected:
            raise ConnectionError("Plant Simulator OPC UA is disconnected")
        values = {
            field: await node.read_value()
            for field, node in self._input_nodes.items()
        }
        values["sensor_quality"] = SensorQuality(str(values["sensor_quality"]))
        values["plant_sequence"] = int(values["plant_sequence"])
        return PlantInputImage(**values)

    async def write_outputs(self, outputs: PlcOutputImage) -> None:
        if not self.connected:
            raise ConnectionError("Plant Simulator OPC UA is disconnected")
        for field, node in self._output_nodes.items():
            await node.write_value(getattr(outputs, field))

    async def command(self, command: str) -> None:
        def send() -> None:
            request = Request(
                f"{self.api_url}/api/v1/commands/{command}",
                data=json.dumps({}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=self.request_timeout_seconds) as response:
                if response.status >= 300:
                    raise ConnectionError(f"Plant command failed with HTTP {response.status}")

        await asyncio.to_thread(send)
