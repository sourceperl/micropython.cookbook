def crc16(data: bytearray):
    crc = 0xFFFF
    for byte in bytearray(data):
        next_byte = byte
        crc ^= next_byte
        for i in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc


def frame2hex(frame: bytearray): 
    return '-'.join(['%02X' % b for b in frame])


def check_crc_ok(frame: bytearray): 
    try:
        assert len(frame) > 2
        cp_crc = crc16(frame[:-2])
        rx_crc = int.from_bytes(frame[-2:], 'little')
        return cp_crc == rx_crc
    except:
        return False