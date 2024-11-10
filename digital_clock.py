import sys
import colorsys
import simplepyble
import time
import math
from collections import OrderedDict, defaultdict
SERVICE_UUID = "000000fa-0000-1000-8000-00805f9b34fb"
WRITE_CMD_UUID = "0000fa02-0000-1000-8000-00805f9b34fb"
# Function to write a bulk packet to BLE device
def write_packet_bulk(packet_list, peripheral):
    for packet in packet_list:
        peripheral.write_request(SERVICE_UUID, WRITE_CMD_UUID, bytes(packet))
# Function to paint pixels on the display
def graffiti_paint_bulk(pixels, peripheral):
    packet_list = []
    for (x, y), rgb_tuple in pixels.items():
        if x < 0 or x >= 32 or y < 0 or y >= 32:
            continue  # Ensure coordinates are within bounds
        graffiti_packet = bytearray.fromhex("0a 00 05 01 00 ff 00 00 1f 1f")
        r, g, b = rgb_tuple
        graffiti_packet[5] = r
        graffiti_packet[6] = g
        graffiti_packet[7] = b
        graffiti_packet[8] = x
        graffiti_packet[9] = y
        packet_list.append(graffiti_packet)
    # Send all packets in one go to minimize latency
    write_packet_bulk(packet_list, peripheral)
# Predefined bitmaps for digits 0-9, colon, and smaller digits for seconds
NUMBER_BITMAPS = {
    'small_0': [
        "111",
        "101",
        "101",
        "101",
        "111"
    ],
    'small_1': [
        "010",
        "110",
        "010",
        "010",
        "111"
    ],
    'small_2': [
        "111",
        "001",
        "111",
        "100",
        "111"
    ],
    'small_3': [
        "111",
        "001",
        "111",
        "001",
        "111"
    ],
    'small_4': [
        "101",
        "101",
        "111",
        "001",
        "001"
    ],
    'small_5': [
        "111",
        "100",
        "111",
        "001",
        "111"
    ],
    'small_6': [
        "111",
        "100",
        "111",
        "101",
        "111"
    ],
    'small_7': [
        "111",
        "001",
        "001",
        "010",
        "010"
    ],
    'small_8': [
        "111",
        "101",
        "111",
        "101",
        "111"
    ],
    'small_9': [
        "111",
        "101",
        "111",
        "001",
        "111"
    ],
    'small_:': [
        "0",
        "1",
        "0",
        "1",
        "0"
    ]
}
# Function to generate a bulk pixel map for the current time
def generate_pixel_map(current_time, x_offset=2, y_offset=1):
    pixel_map = defaultdict(lambda: (0, 0, 0))
    # Clear the entire screen first to avoid overdrawing
    for x in range(32):
        for y in range(32):
            pixel_map[(x, y)] = (0, 0, 0)
    # Draw entire time in smaller font in one line at the top
    for char in current_time:
        small_char = f"small_{char}"
        if small_char in NUMBER_BITMAPS:
            bitmap = NUMBER_BITMAPS[small_char]
            for y, row in enumerate(bitmap):
                for x, pixel in enumerate(row):
                    if pixel == '1':
                        pixel_map[(x + x_offset, y + y_offset)] = (255, 255, 255)
            # Add spacing between characters, but no space after colon
            if char == ':':
                x_offset += 2  # Colon width, no additional space
            else:
                x_offset += 4  # Character width plus space
    return pixel_map
# Function to draw current time on the matrix
def draw_time(peripheral):
    previous_state = defaultdict(lambda: (0, 0, 0))  # Store the previous state of each pixel
    while True:
        # Get current time in HH:MM:SS format
        current_time = time.strftime("%H:%M:%S", time.localtime())
        # Generate pixel map for the current time
        pixel_map = generate_pixel_map(current_time)
        # Only update the pixels that have changed
        changes = {coord: color for coord, color in pixel_map.items() if previous_state[coord]
!= color}
        if changes:
            graffiti_paint_bulk(changes, peripheral)
            previous_state.update(changes)
        time.sleep(0.025)  # Reduced sleep time to increase refresh speed
if __name__ == "__main__":
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapters found.")
        sys.exit(1)
    adapter = adapters[0]
    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()
    for peripheral in peripherals:
        if peripheral.identifier().startswith("IDM-"):
            print(f"Connecting to {peripheral.identifier()} [{peripheral.address()}]")
            peripheral.connect()
            try:
                draw_time(peripheral)
            finally:
                print("Disconnecting from the device...")
                peripheral.disconnect()
