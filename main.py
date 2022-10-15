from emotiva_rs232 import *
import asyncio
import logging
import time
import threading
import keyboard

def run_event_loop(loop):
    loop.run_forever()

def main():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # test using a serial connection:
    #device = FusionFlexDevice(ConnectionType.SERIAL, "COM1")
    # test using UDP:
    device = FusionFlexDevice(ConnectionType.UDP,
        local_ip='127.0.0.1', local_port=0,
        remote_hostname= "127.0.0.1", remote_port=5000)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(device.async_start())
    threading.Thread(target=run_event_loop, args=[loop]).start()
    try:
        print('Options: ')
        print("  (P) Power ON")
        print("  (p) Power OFF")
        print("  (+) Volume Up")
        print("  (-) Volume Down")
        print("  (0-9) Volume 0%%-90%%")
        print("  (_) Volume 100%%")
        print("  (M) Mute ON")
        print("  (m) Mute OFF")
        print("  (n) Mute Toggle")
        print("  (~) Auto-Select Input")
        print("  (!) Select Input 1")
        print("  (@) Select Input 2")
        while True:
            key = keyboard.read_key()
            if key == "shift":
                continue
            elif key == "P":
                device.turn_on()
            elif key == "p":
                device.turn_off()
            elif key == "+":
                device.volume_up()
            elif key == "-":
                device.volume_down()
            elif key == "0":
                device.set_volume_level_fraction(0.0)
            elif key == "1":
                device.set_volume_level_fraction(0.1)
            elif key == "2":
                device.set_volume_level_fraction(0.2)
            elif key == "3":
                device.set_volume_level_fraction(0.3)
            elif key == "4":
                device.set_volume_level_fraction(0.4)
            elif key == "5":
                device.set_volume_level_fraction(0.5)
            elif key == "6":
                device.set_volume_level_fraction(0.6)
            elif key == "7":
                device.set_volume_level_fraction(0.7)
            elif key == "8":
                device.set_volume_level_fraction(0.8)
            elif key == "9":
                device.set_volume_level_fraction(0.9)
            elif key == "_":
                device.set_volume_level_fraction(1.0)
            elif key == "9":
                device.set_volume_level_fraction(0.9)
            elif key == "_":
                device.set_volume_level_fraction(1.0)
            elif key == "M":
                device.mute_on()
            elif key == "m":
                device.mute_off()
            elif key == "M":
                device.mute_on()
            elif key == "n":
                device.mute_toggle()
            elif key == "~":
                device.select_input_source(FusionFlexSourceMode.AUTO)
            elif key == "!":
                device.select_input_source(FusionFlexSourceMode.INPUT_1)
            elif key == "@":
                device.select_input_source(FusionFlexSourceMode.INPUT_2)
            else:
                continue
            time.sleep(0.5)
            print(device.status)
    except InterruptedError:
        loop.stop()
    

if __name__ == '__main__':
    main()