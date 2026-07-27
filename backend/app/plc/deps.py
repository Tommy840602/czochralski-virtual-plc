from functools import lru_cache

from app.core.config import get_settings
from app.plc.runtime import VirtualPlcRuntime


@lru_cache
def get_plc_runtime() -> VirtualPlcRuntime:
    return VirtualPlcRuntime(get_settings())
