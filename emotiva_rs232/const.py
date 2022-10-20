"""Contants for the Emotiva-RS232 package."""

from enum import IntEnum


class ConnectionType(IntEnum):
    """
    Enumeration of supported connection types for communicating with
    the Emotiva Fusion Flex stereo amplifier.
    """

    SERIAL = 0
    UDP = 1
