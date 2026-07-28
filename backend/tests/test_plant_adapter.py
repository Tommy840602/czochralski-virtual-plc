import asyncio
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

import app.plc.adapter as adapter_module
from app.plc.adapter import OpcUaPlantAdapter


def plant_adapter() -> OpcUaPlantAdapter:
    return OpcUaPlantAdapter(
        endpoint="opc.tcp://plant-simulator:4840/server/",
        namespace_uri="urn:test:plant",
        api_url="http://plant-simulator:8090",
    )


def test_command_preserves_plant_rejection_detail(monkeypatch):
    def reject(*_args, **_kwargs):
        raise HTTPError(
            url="http://plant-simulator:8090/api/v1/commands/start",
            code=409,
            msg="Conflict",
            hdrs=None,
            fp=BytesIO(b'{"detail":"Reset is required before start"}'),
        )

    monkeypatch.setattr(adapter_module, "urlopen", reject)

    with pytest.raises(ValueError, match="Reset is required before start"):
        asyncio.run(plant_adapter().command("start"))


def test_command_reports_unavailable_plant_api(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise URLError("connection refused")

    monkeypatch.setattr(adapter_module, "urlopen", unavailable)

    with pytest.raises(ConnectionError, match="command API is unavailable"):
        asyncio.run(plant_adapter().command("start"))
