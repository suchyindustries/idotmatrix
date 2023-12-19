#!/usr/bin/env python3
from Crypto.Cipher import AES
import sys
import colorsys
import simplepyble
import time
import random
import math
from collections import OrderedDict

# Some communication with the controller is done using AES ECB encryption
# Key extracted from the AES library used by the Android app
SECRET_ENCRYPTION_KEY = bytes([0x34, 0x52, 0x2A, 0x5B, 0x7A, 0x6E, 0x49, 0x2C, 0x08, 0x09, 0x0A, 0x9D, 0x8D, 0x2A, 0x23, 0xF8])

SERVICE_UUID             = "000000fa-0000-1000-8000-00805f9b34fb"
WRITE_CMD_UUID           = "0000fa02-0000-1000-8000-00805f9b34fb" # For sending commands to the controller
#WRITE_DATA_UUID          = "d44bc439-abfd-45a2-b575-92541612960a" # For sending colour data to the controller
NOTIFICATION_UUID        = "0000fa03-0000-1000-8000-00805f9b34fb" # The UUID that I think notifications are sent from
#NOTIFICATION_UUID        = "0000fff0-0000-1000-8000-00805f9b34fb" # For enabling notifications from the controller
#NOTIFICATION_UUID_2      = "0000ae00-0000-1000-8000-00805f9b34fb" #  I think this is just OTA notifications, and not supported by this script

COLOUR_DATA = bytearray.fromhex("16 00 7F 00 00 7F 51 00 7F 7F 00 00 7F 00 00 00 7F 7F 00 7F 7F 7F 7F 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00")
print (f"Length of colour data: {len(COLOUR_DATA)}")
# Red, Orange, Yellow, Green, Blue, Red, White - or thereabouts

def write_packet(packet):
    #packet = encrypt_aes_ecb(packet)
    peripheral.write_request(SERVICE_UUID, WRITE_CMD_UUID, bytes(packet))

def write_colour_data(packet):
    peripheral.write_request(SERVICE_UUID, WRITE_DATA_UUID, bytes(packet))

def build_colour_data_packet(colour_list):
    # Pass in a list of tuples with the 8 bit rgb colours you want
    # e.g. my_colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    length = len(colour_list)
    print(f"Length: {length}")
    if length > 32:
        print("Too many colours. Truncating to 32")
        colour_list = colour_list[:31]
        length = 32
    NEW_COLOUR_DATA = []
    NEW_COLOUR_DATA.append(length*3)
    NEW_COLOUR_DATA.append(0)
    for each in colour_list:
        r, g, b = each
        NEW_COLOUR_DATA.append(r)
        NEW_COLOUR_DATA.append(g)
        NEW_COLOUR_DATA.append(b)

    # Clear out the rest of the packet
    if length < 32:
        for i in range(length, 32):
            NEW_COLOUR_DATA.extend([0, 0, 0])
    return bytearray(NEW_COLOUR_DATA)

def build_rainbow_colour_list(num=31):
    colour_list = []
    colour_divisions = int(360 / num)
    for i in range(num):
        h = i * colour_divisions
        r, g, b = colorsys.hsv_to_rgb(h / 360, 1, 1)
        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)
        colour_list.append((r, g, b))
    print(f"Colour list: {colour_list}")
    return colour_list

def generate_spiral_coordinates(grid_size=32, num_points=500):
    x_center, y_center = grid_size // 2, grid_size // 2
    spiral_coordinates = []

    for t in range(num_points):
        angle = 0.1 * t
        radius = 0.5 * angle

        x = int(x_center + radius * math.cos(angle))
        y = int(y_center + radius * math.sin(angle))

        if 0 <= x < grid_size and 0 <= y < grid_size:
            spiral_coordinates.append((x, y))

    return list(OrderedDict.fromkeys(spiral_coordinates))

def graffiti_paint(rgb_tuple, x, y):
    # Sets a single pixel to a colour and mode
    """
        y (starting at zero) ---------------|
        x (starting at zero) ------------|  |
        blue -------------------------|  |  |
        green ---------------------|  |  |  |
        red --------------------|  |  |  |  |
        header --|------------| |  |  |  |  |
                `0a 00 05 01 00 ff 00 00 1f 1f`
                 0  1  2  3  4  5  6  7  8  9
    """
    graffiti_packet = bytearray.fromhex("0a 00 05 01 00 ff 00 00 1f 1f")
    print(f"X: {x}, Y: {y}")
    print(f"RGB: {rgb_tuple}")
    if x > 31:
        x = 31
    if y > 31:
        y = 31
    r, g, b = rgb_tuple
    graffiti_packet[5] = r
    graffiti_packet[6] = g
    graffiti_packet[7] = b
    graffiti_packet[8] = x
    graffiti_packet[9] = y
    write_packet(graffiti_packet)

def decrypt_aes_ecb(ciphertext):
    cipher = AES.new(SECRET_ENCRYPTION_KEY, AES.MODE_ECB)
    plaintext = cipher.decrypt(ciphertext)
    return plaintext

def encrypt_aes_ecb(plaintext):
    cipher = AES.new(SECRET_ENCRYPTION_KEY, AES.MODE_ECB)
    ciphertext = cipher.encrypt(plaintext)
    print(f"Encrypted: {ciphertext.hex()}")
    return ciphertext

def switch_on(state):
    packet = bytearray.fromhex("05 00 07 01 01")
    if state is True:
        packet[4] = 1
    else:
        packet[4] = 0
    write_packet(packet)

def set_colour(r, g, b):
    # Device seems to use 5 bit colour values, we will convert from 8 bit
    # I don't know if it's 5 bits per channel, or if green has 6 bits.  I'm going to
    # assume 5 bits per channel for now.
    # Also the colour packets seem to be duplicated.  Not sure why yet.  Need to play
    # The Android app does this:
    """
        byte[] bArr = {15, 83, 71, 76, 83, (byte) lightsColor.getModelIndex(), (byte) (1 ^ z), 100, (byte) lightsColor.getSpeed(), red, green, blue, red2, green2, blue2, (byte) lightsColor.getSaturation()};
    """
    #                           0   1   2   3   4   5   6   7   8   9   10  11  12  13  14  15
    # red 9 & 12 ------------------------------------------v--------v
    # green 10 & 13 ---------------------------------------|--v-----|--v
    # blue 11 & 14 ----------------------------------------|--|--v--|--|--v
    packet = bytearray.fromhex("0F 53 47 4C 53 00 00 64 50 1F 00 00 1F 00 00 32")
    # brightness ---------------------------------|-----|--------------------^ (0-100?)  NOPE - this is not brightness.
    # speed --------------------------------------|-----^
    # reverse ------------------------------------^
    # r = int(r >> 3) # This is deliberately limited in the app to 5 bits.  But 8 bits works just fine!
    # g = int(g >> 3)
    # b = int(b >> 3)
    packet[9] = r
    packet[12] = r
    packet[10] = g
    packet[13] = g
    packet[11] = b
    packet[14] = b
    write_packet(packet)

def set_effect(effect, reverse=0, speed=50, saturation=50, colour_data=COLOUR_DATA):
    #                                          0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15
    #                                          0A 4D 55 4C 54 08 00 64 50 07 32 00 00 00 00 00
    # header  ---------------------------------|            | |  |  |   |  |  | |            |
    # effect number- -----------------------------------------|  |  |   |  |  | |            |
    # reverse? --------------------------------------------------/  |   |  |  | |            |  
    # fixed (led count?) -------------------------------------------/   |  |  | |            |
    # speed ------------------------------------------------------------/  |  | |            |
    # colour array size? --------------------------------------------------/  | |            |
    # saturation (perhaps actually brightness?)-------------------------------/ |            |
    # always zero? -------------------------------------------------------------/------------|
    # NB: Effects seem to only support 7 colours max
    if effect > 11: effect=11 # if you use an effect higher than this, you will fry your lights.  I learned this the hard way.

    packet = bytearray.fromhex("0A 4D 55 4C 54 08 00 64 50 07 32 00 00 00 00 00")
    packet[5]  = effect
    packet[6]  = reverse
    packet[8]  = speed
    packet[10] = saturation
    write_packet(packet)
    # Now we send the colour data
    write_colour_data(colour_data)

def get_version():
    # Read PCB version - should generate a notification with the info
    packet = bytearray.fromhex("03 56 45 00 00 00 00 00 00 00 00 00 00 00 00 00")
    write_packet(packet)
    # Read firmware version - should generate a notification with the info
    packet = bytearray.fromhex("03 56 45 01 00 00 00 00 00 00 00 00 00 00 00 00")
    write_packet(packet)
    
def response_decode(response):
    #print(f"Response: {response.hex()}")
    # The response is encrypted, so decrypt it
    #response = decrypt_aes_ecb(response)
    print(f"Response: {response.hex()}")

def connect_to_device(mac_addr):
    print("Connecting to device" + mac_addr)
    idm_device = Peripheral(mac_addr)
    services = idm_device.getServices()
    for service in services:
        print(service)
        characteristics = service.getCharacteristics()  
        for characteristic in characteristics:
            print(characteristic)
        descriptors = service.getDescriptors()
        for descriptor in descriptors:
            print(descriptor)
    return idm_device

def find_devices():
    idotmatrixes = {}
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            if desc == "Complete Local Name" and value.startswith("LEDnetWF"):
                    print("Found device: %s (%s), RSSI=%d dB" % (dev.addr, value, dev.rssi))
                    idotmatrixes[dev.addr] = dev.rssi

    if len(idotmatrixes) > 0:
        idotmatrixes = dict(sorted(idotmatrixes.items(), key=lambda item: item[1], reverse=True))
        print("\n\n")
        for key, value in idotmatrixes.items():
            print(f"Device: {key}, RSSI: {value}")
    else:
        print("No devices found")

adapters = simplepyble.Adapter.get_adapters()
adapter = adapters[0]

if len(sys.argv) > 1 and sys.argv[1] == "--scan":
    adapter.set_callback_on_scan_start(lambda: print("Scan started"))
    adapter.set_callback_on_scan_stop(lambda: print("Scan stopped"))
    adapter.set_callback_on_scan_found(lambda peripheral: print(f"Found {peripheral.identifier()} [{peripheral.address()}]"))
    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()
    print("The following devices  were found:")
    for peripheral in peripherals:
        if peripheral.identifier().startswith("IDM-"):
            print(f"\tMAC address: {peripheral.address()}, RSSI: {peripheral.rssi()}")
            manufacturer_data = peripheral.manufacturer_data()
            for manufacturer_id, value in manufacturer_data.items():
                print(f"\t\tManufacturer ID: {manufacturer_id}")
                print(f"\t\tManufacturer data: {value}")
                print(' '.join(format(x, '02x') for x in value))
elif len(sys.argv) > 1 and sys.argv[1] == "--connect":
    # There are no examples of how to instantiate a peripheral object from a mac address
    # it probably can be done, but I can't work it out from the source, so for now
    # just use scan to find it by name
    #r = build_colour_data_packet(build_rainbow_colour_list(100))
    #r = build_rainbow_colour_list(100)
    #print(f"Colour data: {r.hex()}")
    print("Scanning for devices")
    adapter.scan_for(2000)
    peripherals = adapter.scan_get_results()
    for peripheral in peripherals:
        if peripheral.identifier().startswith("IDM-"):
            # this will do
            peripheral.connect()
            print(f"Connected to {peripheral.identifier()}.  MTU: {peripheral.mtu()}")
            time.sleep(3)
            try:
                services = peripheral.services()
                for service in services:
                    print(f"Service: {service.uuid()}")
                    for characteristic in service.characteristics():
                        print(f"\tCharacteristic: {characteristic.uuid()}")
                        for descriptor in characteristic.descriptors():
                            print(f"\t\tDescriptor: {descriptor.uuid()}")
                peripheral.notify(SERVICE_UUID, NOTIFICATION_UUID, response_decode)
                print("Turning on")
                switch_on(True)
                time.sleep(1)
                spiral = generate_spiral_coordinates()
                print(spiral)
                for each in spiral:
                    graffiti_paint((random.randint(0,255), random.randint(0,255), random.randint(0,255)), each[0], each[1])
                    time.sleep(0.1)
                time.sleep(10)
                print("Turning off")
                switch_on(False)
            finally:
                peripheral.disconnect()
else:
    print("Pass in either --scan or --connect")