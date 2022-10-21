"""Common definitions for Emotiva RS232 devices."""

from .const import ConnectionType


class EmotivaDevice:
    """A base class for all Emotiva-RS232 devices."""

    @property
    def connection_type(self) -> ConnectionType:
        """Get connection type."""
        return self._connection_type

    @property
    def serial_port(self) -> str:
        """Get serial device name or path."""
        return self._serial_port

    @property
    def local_ip(self) -> str:
        """Get local IP address."""
        return self._remote_hostname

    @property
    def local_port(self) -> int:
        """Get local UDP/TCP port number."""
        return self._remote_port

    @property
    def remote_hostname(self) -> str:
        """Get remote hostname."""
        return self._remote_hostname

    @property
    def remote_port(self) -> int:
        """Get remote UDP/TCP port number."""
        return self._remote_port

    def __init__(
        self,
        connection_type: ConnectionType,
        serial_port: str = None,
        local_ip: str = None,
        local_port: int = 0,
        remote_hostname: str = None,
        remote_port: int = 0,
    ) -> None:
        self._connection_type: ConnectionType = connection_type
        self._serial_port = serial_port
        self._local_ip: str = local_ip if local_ip is not None else '0.0.0.0'
        self._local_port: int = local_port
        self._remote_hostname: str = remote_hostname
        self._remote_port: int = remote_port

    async def async_start(self):
        """Start communication with the device."""
        raise NotImplementedError()

    async def async_stop(self):
        """Stop communication with the device."""
        raise NotImplementedError()
