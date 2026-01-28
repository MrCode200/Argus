from typing_extensions import NamedTuple


class DeviceInfo(NamedTuple):
    name: str
    degrees_per_step: int | float


class EyeActions(NamedTuple):
    PING = "ping"
    GET_DEVICE_INFO = "get_device_info"
    CALIBRATE = "calibrate"
    STOP = "stop"
