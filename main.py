"""A simple test application for controlling Emotiva Fusion-Flex."""
import asyncio
import logging
import time
import threading
import keyboard
from emotiva_rs232 import (
    ConnectionType,
    FusionFlexDevice,
    FusionFlexSourceMode
)

def _run_event_loop(loop):
    """Helper function for running an event loop in a separate thread."""
    loop.run_forever()

def _status_changed(device: FusionFlexDevice):
    """A callback for receiving device status changes."""
    print(device.status)

_OPTIONS = {
    "h": ("Print Options", lambda _: _print_options()),
    "P": ("Power ON", lambda device: device.turn_on()),
    "p": ("Power OFF", lambda device: device.turn_off()),
    "+": ("Volume Up", lambda device: device.volume_up()),
    "-": ("Volume Down", lambda device: device.volume_down()),
    "0": ("Volume   0%", lambda device: device.set_volume_level_fraction(0.0)),
    "1": ("Volume  10%", lambda device: device.set_volume_level_fraction(0.1)),
    "2": ("Volume  20%", lambda device: device.set_volume_level_fraction(0.2)),
    "3": ("Volume  30%", lambda device: device.set_volume_level_fraction(0.3)),
    "4": ("Volume  40%", lambda device: device.set_volume_level_fraction(0.4)),
    "5": ("Volume  50%", lambda device: device.set_volume_level_fraction(0.5)),
    "6": ("Volume  60%", lambda device: device.set_volume_level_fraction(0.6)),
    "7": ("Volume  70%", lambda device: device.set_volume_level_fraction(0.7)),
    "8": ("Volume  80%", lambda device: device.set_volume_level_fraction(0.8)),
    "9": ("Volume  90%", lambda device: device.set_volume_level_fraction(0.9)),
    "_": ("Volume 100%", lambda device: device.set_volume_level_fraction(1.0)),
    "M": ("Mute ON", lambda device: device.mute_on()),
    "m": ("Mute OFF", lambda device: device.mute_off()),
    "n": ("Mute Toggle", lambda device: device.mute_toggle()),
    "~": ("Set Source to AUTO",
        lambda device: device.select_input_source(FusionFlexSourceMode.AUTO)),
    "!": ("Set Source to Input 1",
        lambda device: device.select_input_source(FusionFlexSourceMode.INPUT_1)),
    "@": ("Set Source to Input 2",
        lambda device: device.select_input_source(FusionFlexSourceMode.INPUT_2))
}

def _print_options():
    print("Options:")
    for option in _OPTIONS.items():
        key = option[0]
        desc_and_func = option[1]
        print(f'  ({key}) {desc_and_func[0]}')

def main():
    """Main function."""
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # test using a serial connection:
    #device = FusionFlexDevice(ConnectionType.SERIAL, "COM1")
    # test using UDP:
    device = FusionFlexDevice(ConnectionType.UDP,
        remote_hostname= "127.0.0.1", remote_port=5000)
    device.set_status_changed(_status_changed)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(device.async_start())
    threading.Thread(target=_run_event_loop, args=[loop]).start()
    try:
        _print_options()
        while True:
            key = keyboard.read_key()
            if key == "shift":
                continue # an optiomization - shift can be pressed often.
            option =  _OPTIONS.get(key)
            if option is None:
                continue # invalid input - just ignore it.
            description = option[0]
            action = option[1]
            # execute the chosen option:
            print(description)
            action(device)
            # sleep a little between executions:
            time.sleep(0.5)
    except InterruptedError:
        loop.stop()


if __name__ == '__main__':
    main()
