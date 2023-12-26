import struct


# some consts
ASCII_LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
# function codes
READ_COILS = 0x01
READ_DISCRETE_INPUTS = 0x02
READ_HOLDING_REGISTERS = 0x03
READ_INPUT_REGISTERS = 0x04
WRITE_SINGLE_COIL = 0x05
WRITE_SINGLE_REGISTER = 0x06
WRITE_MULTIPLE_COILS = 0x0F
WRITE_MULTIPLE_REGISTERS = 0x10
WRITE_READ_MULTIPLE_REGISTERS = 0x17
ENCAPSULATED_INTERFACE_TRANSPORT = 0x2B
# custom function codes
GET_ALL_HOURLY_STATION_DATA = 0x64
GET_ALL_DAILY_STATION_DATA = 0x65
GET_ALL_HOURLY_LINE_DATA = 0x66
GET_ALL_DAILY_LINE_DATA = 0x67
GET_ALL_GAS_AUX_HOURLY_STATION_DATA = 0x68
GET_DETAILED_HOURLY_STATION_DATA = 0x69


# some functions
def crc16(frame: bytes) -> int:
    """Compute CRC16.

    :param frame: frame
    :type frame: bytes
    :returns: CRC16
    :rtype: int
    """
    crc = 0xFFFF
    for next_byte in frame:
        crc ^= next_byte
        for _ in range(8):
            lsb = crc & 1
            crc >>= 1
            if lsb:
                crc ^= 0xA001
    return crc


# some class
class ModbusRTUFrame:
    """ Modbus RTU frame container class. """

    def __init__(self, raw=b'', is_request: bool = False):
        # public
        self.raw = raw
        # flags
        self.is_request = is_request

    def __bool__(self) -> bool:
        return bool(self.raw)

    def __len__(self) -> int:
        return len(self.raw)

    def __repr__(self) -> str:
        return self.as_hex

    @property
    def is_request_as_str(self) -> str:
        """Return request/response type as string."""
        return 'request' if self.is_request else 'response'

    @property
    def pdu(self) -> bytes:
        """Return PDU part of frame."""
        return self.raw[1:-2]

    @property
    def slv_addr(self) -> int or None:
        """Return slave address part of frame."""
        try:
            return self.raw[0]
        except IndexError:
            return

    @property
    def func_code(self) -> int or None:
        """Return function code part of frame."""
        try:
            return self.raw[1]
        except IndexError:
            return

    @property
    def except_code(self) -> int or None:
        """Return except code part of frame."""
        try:
            return self.raw[2]
        except IndexError:
            return

    @property
    def crc_ok(self) -> bool:
        """Check if frame have a valid CRC.

        :return: True if CRC ok
        """
        return crc16(self.raw) == 0

    @property
    def is_valid(self) -> bool:
        """Check if frame is valid.

        :return: True if frame is valid
        """
        return len(self.raw) > 4 and self.crc_ok

    @property
    def as_hex(self) -> str:
        return '-'.join(['%02X' % x for x in self.raw])



class FrameAnalyzer:
    """ Modbus frame processing. """

    class _InternalError(Exception):
        pass

    def __init__(self):
        # current and last frame
        self.frm_now = ModbusRTUFrame()
        self.frm_last = ModbusRTUFrame()
        # private
        # modbus functions maps
        self._func_methods = {READ_COILS: self._msg_read_bits,
                              READ_DISCRETE_INPUTS: self._msg_read_bits,
                              READ_HOLDING_REGISTERS: self._msg_read_words,
                              READ_INPUT_REGISTERS: self._msg_read_words,
                              WRITE_SINGLE_COIL: self._msg_write_single_coil,
                              WRITE_SINGLE_REGISTER: self._msg_write_single_reg,
                              WRITE_MULTIPLE_COILS: self._msg_write_multiple_coils,
                              WRITE_MULTIPLE_REGISTERS: self._msg_write_multiple_registers,}
                              #GET_ALL_HOURLY_STATION_DATA: self._msg_hourly_station_data,
                              #GET_ALL_DAILY_STATION_DATA: self._msg_daily_station_data,
                              #GET_ALL_HOURLY_LINE_DATA: self._msg_hourly_line_data,
                              #GET_ALL_DAILY_LINE_DATA: self._msg_daily_line_data,
                              #GET_ALL_GAS_AUX_HOURLY_STATION_DATA: self._msg_hourly_station_data,
                              #GET_DETAILED_HOURLY_STATION_DATA: self._msg_hourly_station_data}
        self._func_names = {READ_COILS: 'read coils',
                            READ_DISCRETE_INPUTS: 'read discrete inputs',
                            READ_HOLDING_REGISTERS: 'read holding registers',
                            READ_INPUT_REGISTERS: 'read input registers',
                            WRITE_SINGLE_COIL: 'write single coil',
                            WRITE_SINGLE_REGISTER: 'write single register',
                            WRITE_MULTIPLE_COILS: 'write multiple coils',
                            WRITE_MULTIPLE_REGISTERS: 'write multiple registers',
                            WRITE_READ_MULTIPLE_REGISTERS: 'write read multiple registers',
                            ENCAPSULATED_INTERFACE_TRANSPORT: 'encapsulated interface transport',
                            GET_ALL_HOURLY_STATION_DATA: 'hourly station data',
                            GET_ALL_DAILY_STATION_DATA: 'daily station data',
                            GET_ALL_HOURLY_LINE_DATA: 'hourly line data',
                            GET_ALL_DAILY_LINE_DATA: 'daily line data',
                            GET_ALL_GAS_AUX_HOURLY_STATION_DATA: 'aux. hourly station data',
                            GET_DETAILED_HOURLY_STATION_DATA: 'detailed hourly station data'}

    @classmethod
    def _is_valid_tag(cls, tag_name: str) -> bool:
        if tag_name:
            return all((c in ASCII_LETTERS for c in tag_name))
        else:
            return False

    @classmethod
    def _ext_tags(cls, tags_block: bytes) -> dict:
        try:
            tags_d = {}
            for i in range(0, len(tags_block), 10):
                tag_name, tag_value = struct.unpack('<6sf', tags_block[i:i+10])
                tag_name = tag_name.rstrip(b'\x00').decode().rstrip()
                if cls._is_valid_tag(tag_name):
                    tags_d[tag_name] = tag_value
            return tags_d
        except (struct.error, UnicodeDecodeError) as e:
            raise FrameAnalyzer._InternalError(e)

    @classmethod
    def _fmt_tags_as_str(cls, tags: dict) -> str:
        tags_str = ''
        for tag_name, tag_value in tags.items():
            tags_str += ', ' if tags_str else ''
            tags_str += f'{tag_name}={tag_value:.03f}'
        if not tags_str:
            tags_str = 'n/a'
        return tags_str

    def _msg_err(self) -> str:
        f_as_hex = self.frm_now.raw.hex(':')
        return f"bad CRC or too short frame (raw: {f_as_hex})"

    def _msg_except(self) -> str:
        # override request or response flag
        # except frame is always a response
        self.frm_now.is_request = False
        # format analyze message
        return f'response: exception (code 0x{self.frm_now.except_code:02x})'

    def _msg_func_unknown(self) -> str:
        # format message
        return f'{self.frm_now.is_request_as_str}: function not supported'

    def _msg_read_bits(self) -> str:
        # override request or response flag
        # 8 bytes long frame -> request or response, other length -> always a response
        if len(self.frm_now) != 8:
            self.frm_now.is_request = False
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                bit_addr, bit_nb = struct.unpack('>HH', self.frm_now.pdu[1:])
                msg_pdu = f'read {bit_nb} bit(s) at @ 0x{bit_addr:04x} ({bit_addr})'
            except struct.error:
                msg_pdu = 'bad PDU format'
        else:
            # response
            try:
                read_bytes, = struct.unpack('>B', self.frm_now.pdu[1:2])
                bytes_l = struct.unpack(f'>{read_bytes}B', self.frm_now.pdu[2:])
                # format bytes_l as bits list str: "1, 0, 1, 0 ..."
                bits_l = []
                for byte_val in bytes_l:
                    for n in range(8):
                        bits_l.append('1' if (byte_val & (1 << n)) else '0')
                bits_str = ', '.join(bits_l)
                msg_pdu = f'return {len(bits_l)} bit(s) (read bytes={read_bytes}) data: [{bits_str}]'
            except struct.error:
                msg_pdu = 'bad PDU format'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_read_words(self) -> str:
        # override request or response flag
        # 8 bytes long frame -> request, other length -> response
        self.frm_now.is_request = len(self.frm_now) == 8
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                reg_addr, regs_nb = struct.unpack('>HH', self.frm_now.pdu[1:])
                msg_pdu = f'read {regs_nb} register(s) at @ 0x{reg_addr:04x} ({reg_addr})'
            except struct.error:
                msg_pdu = 'bad PDU format'
        else:
            # response
            try:
                read_bytes, = struct.unpack('>B', self.frm_now.pdu[1:2])
                regs_l = struct.unpack(f'>{read_bytes // 2}H', self.frm_now.pdu[2:])
                regs_str = ', '.join([f'{r:d}' for r in regs_l])
                msg_pdu = f'return {len(regs_l)} register(s) (read bytes={read_bytes}) data: [{regs_str}]'
            except struct.error:
                msg_pdu = 'bad PDU format'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_write_single_coil(self) -> str:
        # request and response
        try:
            bit_addr, bit_value, _ = struct.unpack('>HBB', self.frm_now.pdu[1:])
            bit_value_str = '1' if bit_value == 0xFF else '0'
            msg_pdu = f'write {bit_value_str} to coil at @ 0x{bit_addr:04x} ({bit_addr})'
            if not self.frm_now.is_request:
                msg_pdu += ' OK'
        except struct.error:
            msg_pdu = 'bad PDU format'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_write_single_reg(self) -> str:
        # request and response
        try:
            reg_addr, reg_value = struct.unpack('>HH', self.frm_now.pdu[1:])
            msg_pdu = f'write {reg_value} to register at @ 0x{reg_addr:04x} ({reg_addr})'
            if not self.frm_now.is_request:
                msg_pdu += ' OK'
        except struct.error:
            msg_pdu = 'bad PDU format'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_write_multiple_coils(self) -> str:
        # override request or response flag
        # 8 bytes long frame -> response, other length -> request
        self.frm_now.is_request = len(self.frm_now) != 8
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                bit_addr, bits_nb, bytes_nb = struct.unpack('>HHb', self.frm_now.pdu[1:6])
                bytes_l = struct.unpack(f'>{bytes_nb}B', self.frm_now.pdu[6:])
                # format bytes_l as bits list str: "1, 0, 1, 0 ..."
                bits_l = []
                for byte_val in bytes_l:
                    for n in range(8):
                        bits_l.append('1' if (byte_val & (1 << n)) else '0')
                bits_str = ', '.join(bits_l)
                msg_pdu = f'write {bits_nb} bit(s) at @ 0x{bit_addr:04x} ({bit_addr}) data: [{bits_str}]'
            except struct.error:
                msg_pdu = 'bad PDU format'
        else:
            # response
            try:
                bit_addr, bits_nb = struct.unpack('>HH', self.frm_now.pdu[1:5])
                msg_pdu = f'write {bits_nb} bit(s) at @ 0x{bit_addr:04x} ({bit_addr}) OK'
            except struct.error:
                msg_pdu = 'bad PDU format'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_write_multiple_registers(self) -> str:
        # override request or response flag
        # 8 bytes long frame -> response, other length -> request
        self.frm_now.is_request = len(self.frm_now) != 8
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                reg_addr, regs_nb, bytes_nb = struct.unpack('>HHb', self.frm_now.pdu[1:6])
                regs_l = struct.unpack(f'>{bytes_nb//2}H', self.frm_now.pdu[6:])
                regs_str = ', '.join([str(b) for b in regs_l])
                msg_pdu = f'write {regs_nb} register(s) at @ 0x{reg_addr:04x} ({reg_addr}) data: [{regs_str}]'
            except struct.error:
                msg_pdu = 'bad PDU format'
        else:
            # response
            try:
                reg_addr, regs_nb = struct.unpack('>HH', self.frm_now.pdu[1:5])
                msg_pdu = f'write {regs_nb} register(s) at @ 0x{reg_addr:04x} ({reg_addr}) OK'
            except struct.error:
                msg_pdu = 'bad PDU format'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_hourly_station_data(self) -> str:
        # override request or response flag
        # 9 bytes long frame -> request, other length -> response
        self.frm_now.is_request = len(self.frm_now) == 9
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                hour_id, b_qty = struct.unpack('>IB', self.frm_now.pdu[1:6])
                hour_dt = FLX_ORIGIN_DT + timedelta(hours=hour_id)
                msg_pdu = f"hourly data from {hour_dt.strftime('%Hh %d/%m/%Y')} (h_id={hour_id}, b_qty={b_qty})"
            except (struct.error, OverflowError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        else:
            # response
            try:
                b_qty = self.frm_now.pdu[1]
                tags_d = self._ext_tags(self.frm_now.pdu[2:])
                tags_str = self._fmt_tags_as_str(tags_d)
                msg_pdu = f'hourly data is {tags_str} (b_qty={b_qty})'
            except (FrameAnalyzer._InternalError, IndexError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_daily_station_data(self) -> str:
        # override request or response flag
        # 9 bytes long frame -> request, other length -> response
        self.frm_now.is_request = len(self.frm_now) == 9
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                day_id, b_qty = struct.unpack('>IB', self.frm_now.pdu[1:6])
                day_dt = FLX_ORIGIN_DT + timedelta(days=day_id)
                msg_pdu = f"daily data from {day_dt.strftime('%d/%m/%Y')} (d_id={day_id}, b_qty={b_qty})"
            except (struct.error, OverflowError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        else:
            # response
            try:
                b_qty = self.frm_now.pdu[1]
                tags_d = self._ext_tags(self.frm_now.pdu[2:])
                tags_str = self._fmt_tags_as_str(tags_d)
                msg_pdu = f'daily data is {tags_str} (b_qty={b_qty})'
            except (FrameAnalyzer._InternalError, IndexError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_hourly_line_data(self) -> str:
        # override request or response flag
        # 10 bytes long frame -> request, other length -> response
        self.frm_now.is_request = len(self.frm_now) == 10
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                hour_id, line_id, b_qty = struct.unpack('>IBB', self.frm_now.pdu[1:7])
                hour_dt = FLX_ORIGIN_DT + timedelta(hours=hour_id)
                msg_pdu = f"hourly data for line {line_id} from {hour_dt.strftime('%Hh %d/%m/%Y')} (h_id={hour_id}, b_qty={b_qty})"
            except (struct.error, OverflowError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        else:
            # response
            try:
                b_qty = self.frm_now.pdu[1]
                tags_d = self._ext_tags(self.frm_now.pdu[2:])
                tags_str = self._fmt_tags_as_str(tags_d)
                msg_pdu = f'hourly data is {tags_str} (b_qty={b_qty})'
            except (FrameAnalyzer._InternalError, IndexError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def _msg_daily_line_data(self) -> str:
        # override request or response flag
        # 10 bytes long frame -> request, other length -> response
        self.frm_now.is_request = len(self.frm_now) == 10
        # decode frame PDU
        if self.frm_now.is_request:
            # request
            try:
                day_id, line_id, b_qty = struct.unpack('>IBB', self.frm_now.pdu[1:7])
                day_dt = FLX_ORIGIN_DT + timedelta(days=day_id)
                msg_pdu = f"daily data for line {line_id} from {day_dt.strftime('%d/%m/%Y')} (d_id={day_id}, b_qty={b_qty})"
            except (struct.error, OverflowError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        else:
            # response
            try:
                b_qty = self.frm_now.pdu[1]
                tags_d = self._ext_tags(self.frm_now.pdu[2:])
                tags_str = self._fmt_tags_as_str(tags_d)
                msg_pdu = f'daily data is {tags_str} (b_qty={b_qty})'
            except (FrameAnalyzer._InternalError, IndexError) as e:
                msg_pdu = f'bad PDU format (error: "{e}")'
        # format message
        return f'{self.frm_now.is_request_as_str}: {msg_pdu}'

    def func_name_by_id(self, func_id: int) -> str:
        """ Translate function code to name or hex representation. """
        if func_id >= 0x80:
            func_id -= 0x80
        try:
            return f'{self._func_names[func_id]} (0x{func_id:02x})'
        except KeyError:
            return f'0x{func_id:02x}'

    def analyze(self, frame: bytes):
        """ Process current frame and produce a message to stdout. """
        # init ModbusRTUFrame
        self.frm_now = ModbusRTUFrame(frame)
        # init msg with first part header
        msg = ''
        # check frame validity
        if not self.frm_now.is_valid:
            # don't analyze invalid frame
            msg += self._msg_err()
        else:
            # add 2nd part header to msg
            f_name = self.func_name_by_id(self.frm_now.func_code)
            msg += f'slave {self.frm_now.slv_addr} "{f_name}" '
            # fix default request/response flag (can be override in _msg_xxxx func methods)
            slv_addr_chg = self.frm_now.slv_addr != self.frm_last.slv_addr
            func_code_chg = self.frm_now.func_code != self.frm_last.func_code
            self.frm_now.is_request = True if slv_addr_chg or func_code_chg else not self.frm_last.is_request
            # check exception status
            if self.frm_now.func_code >= 0x80:
                # on except
                msg += self._msg_except()
            else:
                # if no except, call the ad-hoc function, if none exists, send an "illegal function" exception
                try:
                    msg += self._func_methods[self.frm_now.func_code]()
                except KeyError:
                    msg += self._msg_func_unknown()
            # keep current frame (with good CRC) for next analyze
            self.frm_last = self.frm_now
        # show message
        return msg
