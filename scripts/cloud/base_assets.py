"""Original background asset compiled with stdlib only, no imported artwork."""
import struct
import zlib

WIDTH, HEIGHT = 1080, 624


def background_png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    scanlines = bytearray()
    for y in range(HEIGHT):
        # Original subtle cream-to-sage vertical gradient.
        pixel = bytes((242 - y * 10 // (HEIGHT - 1), 240 - y * 2 // (HEIGHT - 1), 234 + y * 2 // (HEIGHT - 1)))
        scanlines.extend(b'\0' + pixel * WIDTH)
    header = struct.pack('>IIBBBBB', WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) +
            chunk(b'IDAT', zlib.compress(bytes(scanlines), 9)) + chunk(b'IEND', b''))
