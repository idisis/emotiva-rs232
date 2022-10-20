"""Classes for controlling Emotiva Fusion Flex over RS232."""
import asyncio
from collections.abc import Callable
from enum import Enum, IntEnum
import logging
import re
from serial import (
    PARITY_NONE,
    EIGHTBITS,
    STOPBITS_ONE
)
import serial_asyncio

from .const import ConnectionType
from .emotiva_device import EmotivaDevice

MIN_VOLUME_DB: float = -95.5
MAX_VOLUME_DB: float = 0
BAUD_RATE: int = 9600
WRITE_TIMEOUT: int = 3
_BUFFER_SIZE: int = 16
_ENCODING: str = "ascii"

_MESSAGE_START_STR = "'@"
_MESSAGE_END_STR = "'"

_LOGGER = logging.getLogger(__name__)


class RS232Command(Enum):
    """
    A string-enum class of supported
    RS232 commands for the Emotiva Fusion Flex
    stereo amplifier.
    """

    POWER_ON = "'@112'"
    POWER_OFF = "'@113'"
    SELECT_INPUT_1 = "'@15A'"
    SELECT_INPUT_2 = "'@15B'"
    SELECT_INPUT_AUTO = "'@15Z'"
    MUTE_ON = "'@11Q'"
    MUTE_OFF = "'@11R'"
    MUTE_TOGGLE = "'@11U'"
    VOLUME_UP = "'@11S'"
    VOLUME_DOWN = "'@11T'"
    SET_VOLUME_DB_FORMAT = "'@11P-{0:04.1f}'"


class FusionFlexSourceMode(IntEnum):
    """
    Enumeration of supported input source modes for the Emotiva Fusion Flex
    stereo amplifier
    """

    AUTO = 0
    INPUT_1 = 1
    INPUT_2 = 2


class FusionFlexProtocol(asyncio.Protocol, asyncio.DatagramProtocol):
    """Implementation of the Fusion Flex protocol for asyncio"""

    def __init__(
        self,
        remote_endpoint,
        message_received: Callable[[any, str], None],
        user_token: any = None,
    ):
        self.transport: asyncio.BaseTransport = None
        self._remote_endpoint = remote_endpoint
        self._message_received: Callable[[any, str], None] = message_received
        self._user_token: any = user_token
        self._buffer: str = ""

    def connection_made(self, transport):
        self.transport = transport
        _LOGGER.info("Connected to %s", transport)

    def connection_lost(self, exc):
        if exc is not None:
            _LOGGER.warning("Connection to %s was lost", self.transport)
            _LOGGER.warning(exc, exc_info=True)
        else:
            _LOGGER.warning("Connection to %s closed", self.transport)

    def data_received(self, data):
        self._process_data(data)

    def datagram_received(self, data, addr):
        if self._remote_endpoint == addr:
            self._process_data(data)
        else:
            _LOGGER.debug(
                'received data from unexpected source %s: "%s"', addr, repr(data)
            )

    def error_received(self, exc):
        _LOGGER.exception(exc)

    def pause_writing(self):
        _LOGGER.debug("pause_writing() has been called")

    def resume_writing(self):
        _LOGGER.debug("resume_writing() has been called")

    def _process_message(self, msg: str):
        if self._message_received is not None:
            self._message_received(msg)

    def _process_data(self, data: bytearray):
        data_str: str = data.decode(_ENCODING)
        _LOGGER.debug('Data received: "%s"', data_str)
        first_segment = True
        for segment in data_str.split(_MESSAGE_START_STR):
            if len(segment) == 0:  # empty string - nothing to do.
                first_segment = False
                continue
            if not first_segment:
                # add back the message-start sequence that was
                # removed by the call to split:
                self._buffer = _MESSAGE_START_STR
            if self._buffer.startswith(_MESSAGE_START_STR):
                # look for message end:
                msg_end = segment.find(_MESSAGE_END_STR)
                if msg_end < 0:  # message end is not in data_str
                    # protect against buffer overflow:
                    if len(self._buffer) + len(segment) <= _BUFFER_SIZE:
                        self._buffer += segment
                    else:
                        self._buffer = ""
                    return
                msg = self._buffer + segment
                self._process_message(msg)
                self._buffer = ""
            first_segment = False

    def send(self, command: str):
        """Send a command to the device over the chosen connection type."""
        _LOGGER.debug('Outgoing message to device: [%s]', command)
        command_bytes = command.encode(_ENCODING)
        if isinstance(self.transport, serial_asyncio.SerialTransport):
            transport: serial_asyncio.SerialTransport = self.transport
            transport.write(command_bytes)
        elif isinstance(self.transport, asyncio.DatagramTransport):
            transport: asyncio.DatagramTransport = self.transport
            transport.sendto(command_bytes, self._remote_endpoint)
        else:
            raise NotImplementedError()

class FusionFlexStatus:
    """Represents the status of a Fusion-Flex stereo amplifier."""
    @property
    def is_turned_on(self) -> bool:
        """Indicates whether the device is turned on."""
        return self._is_turned_on

    @property
    def volume_db(self) -> float | None:
        """Gets volume level in decibels."""
        return self._volume_db

    @property
    def volume_fraction(self) -> float | None:
        """Gets volume level as a value between 0 and 1."""
        return FusionFlexDevice.volume_decibels_to_fraction(self._volume_db)

    @property
    def source_mode(self) -> FusionFlexSourceMode | None:
        """Gets input source mode."""
        return self._source_mode

    @property
    def is_muted(self) -> bool | None:
        """Indicates whether the device is muted."""
        return self._is_muted

    @is_turned_on.setter
    def is_turned_on(self, value: bool):
        self._is_turned_on = value

    @volume_db.setter
    def volume_db(self, value: float):
        self._volume_db = value

    @source_mode.setter
    def source_mode(self, value: FusionFlexSourceMode):
        self._source_mode = value

    @is_muted.setter
    def is_muted(self, value: bool):
        self._is_muted = value

    def __init__(self, is_turned_on: bool):
        self._is_turned_on : bool = is_turned_on
        self._volume_db: float | None = None
        self._source_mode:  FusionFlexSourceMode | None = None
        self._is_muted: bool | None = None

    def _get_source_mode_as_json_str(self):
        return "null" if self.source_mode is None else f'"{self.source_mode.name}"'

    def __str__(self):
        return ('{' +
            f'"is_turned_on":{self.is_turned_on}, ' +
            f'"volume_db": {self.volume_db}, ' +
            f'"source_mode": {self._get_source_mode_as_json_str()}, ' +
            f'"is_muted": {self.is_muted}' +
             '}')

class FusionFlexDevice(EmotivaDevice):
    """A class for controlling Emotiva Fusion Flex stereo amplifiers over RS232."""

    @property
    def status(self) -> FusionFlexStatus:
        """Get device status."""
        return self._status

    def set_status_changed(self, status_changed_callback: Callable[[EmotivaDevice],None]):
        """Sets a callback for status change notifications."""
        self._status_changed_callback = status_changed_callback

    @staticmethod
    def volume_fraction_to_decibels(value_fraction: float) -> float:
        """Convert volume given in units of [0..1] to dB."""
        if value_fraction < 0 or value_fraction > 1:
            raise ValueError('fraction must be between 0 and 1.')
        value_decibels = MIN_VOLUME_DB + float(value_fraction) * (
            MAX_VOLUME_DB - MIN_VOLUME_DB
        )
        return value_decibels

    @staticmethod
    def volume_decibels_to_fraction(value_decibels: float) -> float:
        """Convert volume given in dB to a fraction between 0 and 1."""
        if value_decibels < MIN_VOLUME_DB or value_decibels > MAX_VOLUME_DB:
            raise ValueError(f'volume must be between {MIN_VOLUME_DB}dB and {MAX_VOLUME_DB}dB')
        value_fraction = (value_decibels - MIN_VOLUME_DB) / (MAX_VOLUME_DB - MIN_VOLUME_DB)
        return value_fraction

    def __init__(
        self,
        connection_type: ConnectionType,
        serial_port: str = None,
        local_ip: str = None,
        local_port: int = 0,
        remote_hostname: str = None,
        remote_port: int = 0,
    ) -> None:
        super().__init__(
            connection_type=connection_type,
            serial_port=serial_port,
            local_ip=local_ip,
            local_port=local_port,
            remote_hostname=remote_hostname,
            remote_port=remote_port)
        self._status: FusionFlexStatus = None
        self._started: bool = False
        self._transport: asyncio.BaseTransport = None
        self._protocol: FusionFlexProtocol = None
        self._status_changed_callback: Callable[[EmotivaDevice], None] = None

    def _process_message(self, msg: str):
        _LOGGER.debug('Incoming message from device: [{%s}]', msg)
        status = self._status if self._status is not None else FusionFlexStatus(True)
        # check if the response contains the volume level:
        result = re.search(r"^'@11[STP](-\d\d\.[05])'$", msg)
        if result is not None:
            # parse the volume level:
            # - the regex should protect us from bad strings.
            # - we don't check volume range since it's already
            #   limited to -99.5 to 0 dB by the regex.
            status.volume_db = float(result.group(1))
        elif msg == RS232Command.POWER_ON.value:
            status.is_turned_on = True
        elif msg == RS232Command.POWER_OFF.value:
            status.is_turned_on = False
        elif msg == RS232Command.SELECT_INPUT_1.value:
            status.source_mode = FusionFlexSourceMode.INPUT_1
        elif msg == RS232Command.SELECT_INPUT_2.value:
            status.source_mode = FusionFlexSourceMode.INPUT_2
        elif msg == RS232Command.SELECT_INPUT_AUTO.value:
            status.source_mode = FusionFlexSourceMode.AUTO
        elif msg == RS232Command.MUTE_ON.value:
            status.is_muted = True
        elif msg == RS232Command.MUTE_OFF.value:
            status.is_muted = False
        else:
            _LOGGER.warning('Ignoring unknown message: "%s"', msg)
            return
        if msg != RS232Command.POWER_OFF.value:
            status.is_turned_on = True
        self._status = status
        callback = self._status_changed_callback
        if callback is not None:
            callback(self)

    def _send_command(self, command: RS232Command | str):
        if isinstance(command, RS232Command):
            command = command.value
        self._protocol.send(command)

    async def async_start(self):
        """Start communication with the device"""

        if self._started:
            return # already started.
        loop = asyncio.get_event_loop()
        if self._connection_type == ConnectionType.SERIAL:
            self._transport, self._protocol = await serial_asyncio.create_serial_connection(
                loop,
                lambda: FusionFlexProtocol(
                    self._serial_port, self._process_message, self
                ),
                self._serial_port,
                baudrate=BAUD_RATE,
                bytesize=EIGHTBITS,
                parity=PARITY_NONE,
                stopbits=STOPBITS_ONE,
            )
        elif self._connection_type == ConnectionType.UDP:
            local_endpoint = (self._local_ip, self._local_port)
            remote_endpoint = (self._remote_hostname, self._remote_port)
            self._transport, self._protocol = await loop.create_datagram_endpoint(
                lambda: FusionFlexProtocol(
                    remote_endpoint, self._process_message, self
                ),
                local_addr=local_endpoint,
                remote_addr=remote_endpoint,
            )
        else:
            raise NotImplementedError(
                f'unsupported connection type "{self._connection_type}"'
            )
        self._started = True

    def stop(self):
        """Stop communication with the device"""
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._protocol = None

    async def async_stop(self):
        self.stop()

    def turn_on(self):
        """Send turn on command."""
        self._send_command(RS232Command.POWER_ON)

    def turn_off(self):
        """Send turn off command."""
        self._send_command(RS232Command.POWER_OFF)

    def mute_on(self):
        """Send mute on command."""
        self._send_command(RS232Command.MUTE_ON)

    def mute_off(self):
        """Send mute off command."""
        self._send_command(RS232Command.MUTE_OFF)

    def mute_toggle(self):
        """Send mute toggle command."""
        self._send_command(RS232Command.MUTE_TOGGLE)

    def set_volume_level_decibels(self, value):
        """
        Set volume to a specific level in decibels.

        Parameters:
            volume (float): the volume level in decibels (dB).
        """
        # round to the nearest 0.5 dB:
        rounded_value = abs(round(2 * value) / 2.0)
        # create a command string:
        volume_command = RS232Command.SET_VOLUME_DB_FORMAT.value.format(rounded_value)
        # send the command to the device:
        self._send_command(volume_command)

    def set_volume_level_fraction(self, value):
        """
        Set volume to a specific level.

        Parameters:
            value (float): the volume level as a fraction between 0 and 1.
        """
        value_decibels = FusionFlexDevice.volume_fraction_to_decibels(float(value))
        self.set_volume_level_decibels(value_decibels)

    def select_input_source(self, source: FusionFlexSourceMode):
        """Select input source."""
        command: RS232Command
        if source == FusionFlexSourceMode.AUTO:
            command = RS232Command.SELECT_INPUT_AUTO
        elif source == FusionFlexSourceMode.INPUT_1:
            command = RS232Command.SELECT_INPUT_1
        elif source == FusionFlexSourceMode.INPUT_2:
            command = RS232Command.SELECT_INPUT_2
        else:
            raise ValueError(f'unsupported input source "{IntEnum.name(source)}".')
        self._send_command(command)

    def volume_up(self):
        """Increase volume by 0.5dB."""
        self._send_command(RS232Command.VOLUME_UP)

    def volume_down(self):
        """Decrease volume by 0.5dB."""
        self._send_command(RS232Command.VOLUME_DOWN)
