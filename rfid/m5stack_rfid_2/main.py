"""Test of m5stack RFID 2 unit use ws1850s chip (same as RC222)

more info: https://docs.m5stack.com/en/unit/rfid2

MFRC522 class come from: https://github.com/cpranzl/mfrc522_i2c/ (just update for test with micropython)
"""

from machine import I2C, Pin


# some class
class MFRC522:
    # Define register values from datasheet
    COMMAND_REG = 0x01  # Start and stops command execution
    COMIEN_REG = 0x02  # Enable and disable interrupt request control bits
    COMIRQ_REG = 0x04  # Interrupt request bits
    DIVIRQ_REG = 0x05  # Interrupt request bits
    ERROR_REG = 0x06  # Error bits showing the error status of the last command
    STATUS2_REG = 0x08  # Receiver and transmitter status bits
    FIFODATA_REG = 0x09  # Input and output of 64 byte FIFO buffer
    FIFOLEVEL_REG = 0x0A  # Number of bytes stored in the FIFO buffer
    CONTROL_REG = 0x0C  # Miscellaneous control register
    BITFRAMING_REG = 0x0D  # Adjustments for bit-oriented frames
    MODE_REG = 0x11  # Defines general modes for transmitting and receiving
    TXCONTROL_REG = 0x14  # Controls the logical behavior of the antenna pins
    TXASKREG = 0x15  # Controls the setting of the transmission modulation
    CRCRESULT_MSB_REG = 0x21  # Shows the MSB of the CRC calculation
    CRCRESULT_LSB_REG = 0x22  # Shows the LSB of the CRC calculation
    TMODE_REG = 0x2A  # Defines settings for the internal timer
    TPRESCALER_REG = 0x2B  # Defines settings for internal timer
    TRELOAD_H_REG = 0x2C  # Defines 16-bit timer reload value
    TRELOAD_L_REG = 0x2D  # Defines 16-bit timer reload value
    VERSION_REG = 0x37  # Shows the software version

    # MFRC522 Commands
    MFRC522_IDLE = 0x00  # No actions, cancels current command execution
    MFRC522_CALCCRC = 0x03  # Activates the CRC coprocessor and performs
    # a self test
    MFRC522_TRANSCEIVE = 0x0C  # Transmits data from FIFO buffer to
    # anntenna and automatically activates the receiver after
    # transmission
    MFRC522_MFAUTHENT = 0x0E  # Performs the MIFARE standard authentication
    # as a reader
    MFRC522_SOFTRESET = 0x0F  # Resets the MFRC522

    # MIFARE Classic Commands
    MIFARE_REQUEST = [0x26]
    MIFARE_WAKEUP = [0x52]
    MIFARE_ANTICOLCL1 = [0x93, 0x20]
    MIFARE_SELECTCL1 = [0x93, 0x70]
    MIFARE_ANTICOLCL2 = [0x95, 0x20]
    MIFARE_SELECTCL2 = [0x95, 0x70]
    MIFARE_HALT = [0x50, 0x00]
    MIFARE_AUTHKEY1 = [0x60]
    MIFARE_AUTHKEY2 = [0x61]
    MIFARE_READ = [0x30]
    MIFARE_WRITE = [0xA0]
    MIFARE_DECREMENT = [0xC0]
    MIFARE_INCREMENT = [0xC1]
    MIFARE_RESTORE = [0xC2]
    MIFARE_TRANSFER = [0xB0]

    # Mifare 1K EEPROM is arranged of 16 sectors. Each sector has 4 blocks and
    # each block has 16-byte. Block 0 is a special read-only data block that
    # keeps the manufacturer data and the UID of the tag. The sector trailer
    # block, the last block of the sector, holds the access conditions and two
    # of the authentication keys for that particular sector
    MIFARE_1K_MANUFAKTURERBLOCK = [0]
    MIFARE_1K_SECTORTRAILER = [3, 7, 11, 15, 19, 23, 27, 31, 35,
                               39, 43, 47, 51, 55, 59, 63]
    MIFARE_1K_DATABLOCK = [1, 2, 4, 5, 6, 8, 9, 10, 12, 13,
                           14, 16, 17, 18, 20, 21, 22,  24,  25,  26,
                           28, 29, 30, 32, 33, 34, 36,  37,  38,  40,
                           41, 42, 44, 45, 46, 48, 49,  50,  52,  53,
                           54, 56, 57, 58, 60, 61, 62]

    # Mifare 4K EEPROM is arranged of 40 sectors. From sector 0 to 31, memory
    # organization is similar to Mifare 1K, each sector has 4 blocks. From
    # sector 32 to 39, each sector has 16 blocks
    MIFARE_4K_MANUFAKTURERBLOCK = [0]
    MIFARE_4K_SECTORTRAILER = [3, 7, 11, 15, 19, 23, 27, 31, 35, 39,
                               43, 47, 51, 55, 59, 63, 67, 71, 75, 79,
                               83, 87, 91, 95, 99, 103, 107, 111, 115, 119,
                               123, 127, 143, 159, 175, 191, 207, 223, 239,
                               255]
    MIFARE_4K_DATABLOCK = [1,  2, 4, 5, 6, 8, 9, 10, 12, 13,
                           14, 16, 17, 18, 20, 21, 22, 24, 25, 26,
                           28, 29, 30, 32, 33, 34, 36, 37, 38, 40,
                           41, 42, 44, 45, 46, 48, 49, 50, 52, 53,
                           54, 56, 57, 58, 60, 61, 62, 64, 65, 66,
                           68, 69, 70, 72, 73, 74, 76, 77, 78, 80,
                           81, 82, 84, 85, 86, 88, 89, 90, 92, 93,
                           94, 96, 97, 98, 100, 101, 102, 104, 105, 106,
                           108, 109, 110, 112, 113, 114, 116, 117, 118, 120,
                           121, 122, 124, 125, 126, 128, 129, 130, 131, 132,
                           133, 134, 135, 136, 137, 138, 139, 140, 141, 142,
                           144, 145, 146, 147, 148, 149, 150, 151, 152, 153,
                           154, 155, 156, 157, 158, 160, 161, 162, 163, 164,
                           165, 166, 167, 168, 169, 170, 171, 172, 173, 174,
                           176, 177, 178, 179, 180, 181, 182, 183, 184, 185,
                           186, 187, 188, 189, 190, 192, 193, 194, 195, 196,
                           197, 198, 199, 200, 201, 202, 203, 204, 205, 206,
                           208, 209, 210, 211, 212, 213, 214, 215, 216, 217,
                           218, 219, 220, 221, 222, 224, 225, 226, 227, 228,
                           229, 230, 231, 232, 233, 234, 235, 236, 237, 238,
                           240, 241, 242, 243, 244, 245, 246, 247, 248, 249,
                           250, 251, 252, 253, 254]

    MIFARE_KEY = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

    MIFARE_OK = 0
    MIFARE_NOTAGERR = 1
    MIFARE_ERR = 2

    MAX_LEN = 16

    def __init__(self, bus, addr):
        self.i2c_bus = bus
        self.i2c_addr = addr
        self.__MFRC522_init()

    def get_reader_version(self):
        return self.__MFRC522_read(self.VERSION_REG)

    def scan(self):
        """ Scans for a card and returns the UID"""
        status = None
        backData = []
        backBits = None

        # None bits of the last byte
        self.__MFRC522_write(self.BITFRAMING_REG, 0x07)

        buffer = []
        buffer.extend(self.MIFARE_REQUEST)

        (status, backData, backBits) = self.__transceiveCard(buffer)

        if ((status != self.MIFARE_OK) | (backBits != 0x10)):
            status = self.MIFARE_ERR

        return (status, backData, backBits)

    def __serialNumberValid(self, serialNumber):
        """ Checks if the serial number is valid """
        i = 0
        serialCheck = 0

        while (i < (len(serialNumber) - 1)):
            serialCheck = serialCheck ^ serialNumber[i]
            i = i + 1
        if (serialCheck != serialNumber[i]):
            return False
        else:
            return True

    def identify(self):
        """ Receives the serial number of the card"""
        status = None
        backData = []
        backBits = None

        # All bits of the last byte
        self.__MFRC522_write(self.BITFRAMING_REG, 0x00)

        buffer = []
        buffer.extend(self.MIFARE_ANTICOLCL1)

        (status, backData, backBits) = self.__transceiveCard(buffer)

        if (status == self.MIFARE_OK):
            if (self.__serialNumberValid(backData)):
                status = self.MIFARE_OK
            else:
                status = self.MIFARE_ERR

        return (status, backData, backBits)

    def __transceiveCard(self, data):
        """ Transceives data trough the reader/writer from and to the card """
        status = None
        backData = []
        backBits = None

        IRqInv = 0x80  # Signal on pin IRQ is inverted
        TxIEn = 0x40  # Allow the transmitter to interrupt requests
        RxIEn = 0x20  # Allow the receiver to interrupt requests
        IdleIEn = 0x10  # Allow the idle interrupt request
        LoAlertIEn = 0x04  # Allow the low Alert interrupt request
        ErrIEn = 0x02  # Allow the error interrupt request
        TimerIEn = 0x01  # Allow the timer interrupt request
        self.__MFRC522_write(self.COMIEN_REG, (IRqInv |
                                              TxIEn |
                                              RxIEn |
                                              IdleIEn |
                                              LoAlertIEn |
                                              ErrIEn |
                                              TimerIEn))

        # Indicates that the bits in the ComIrqReg register are set
        Set1 = 0x80
        self.__MFRC522_clearBitMask(self.COMIRQ_REG, Set1)

        # Immediatly clears the internal FIFO buffer's read and write pointer
        # and ErrorReg register's BufferOvfl bit
        FlushBuffer = 0x80
        self.__MFRC522_setBitMask(self.FIFOLEVEL_REG, FlushBuffer)

        # Cancel running commands
        self.__MFRC522_write(self.COMMAND_REG, self.MFRC522_IDLE)

        # Write data in FIFO register
        for i in range(0, len(data)):
            self.__MFRC522_write(self.FIFODATA_REG, data[i])

        # Countinously repeat the transmission of data from the FIFO buffer and
        # the reception of data from the RF field.
        self.__MFRC522_write(self.COMMAND_REG, self.MFRC522_TRANSCEIVE)

        # Starts the transmission of data, only valid in combination with the
        # Transceive command
        StartSend = 0x80
        self.__MFRC522_setBitMask(self.BITFRAMING_REG, StartSend)

        # The timer has decrement the value in TCounterValReg register to zero
        TimerIRq = 0x01
        # The receiver has detected the end of a valid data stream
        RxIRq = 0x20
        # A command was terminated or unknown command is started
        IdleIRq = 0x10

        # Wait for an interrupt
        i = 2000
        while True:
            comIRqReg = self.__MFRC522_read(self.COMIRQ_REG)
            if (comIRqReg & TimerIRq):
                # Timeout
                break
            if (comIRqReg & RxIRq):
                # Valid data available in FIFO
                break
            if (comIRqReg & IdleIRq):
                # Command terminate
                break
            if (i == 0):
                # Watchdog expired
                break
            i -= 1

        # Clear the StartSend bit in BitFramingReg register
        self.__MFRC522_clearBitMask(self.BITFRAMING_REG, StartSend)

        # Retrieve data from FIFODATAREG
        if (i != 0):
            # The host or a MFRC522's internal state machine tries to write
            # data to the FIFO buffer even though it is already full
            BufferOvfl = 0x10
            # A bit collision is detected
            ColErr = 0x08
            # Parity check failed
            ParityErr = 0x02
            # Set to logic 1 if the SOF is incorrect
            ProtocolErr = 0x01

            errorTest = (BufferOvfl | ColErr | ParityErr | ProtocolErr)
            errorReg = self.__MFRC522_read(self.ERROR_REG)

            # Test if any of the errors above happend
            if (~(errorReg & errorTest)):
                status = self.MIFARE_OK

                # Indicates any error bit in thr ErrorReg register is set
                ErrIRq = 0x02

                # Test if the timer expired and an error occured
                if (comIRqReg & TimerIRq & ErrIRq):
                    status = self.MIFARE_NOTAGERR

                fifoLevelReg = self.__MFRC522_read(self.FIFOLEVEL_REG)

                # Edge cases
                if fifoLevelReg == 0:
                    fifoLevelReg = 1
                if fifoLevelReg > self.MAX_LEN:
                    fifoLevelReg = self.MAX_LEN

                # Indicates the number of valid bits in the last received byte
                RxLastBits = 0x08

                lastBits = self.__MFRC522_read(self.CONTROL_REG) & RxLastBits

                if (lastBits != 0):
                    backBits = (fifoLevelReg - 1) * 8 + lastBits
                else:
                    backBits = fifoLevelReg * 8

                # Read data from FIFO register
                for i in range(0, fifoLevelReg):
                    backData.append(self.__MFRC522_read(self.FIFODATA_REG))

            else:
                status = self.MIFARE_ERR

        return (status, backData, backBits)

    def __calculateCRC(self, data):
        """ Uses the reader/writer to calculate CRC """
        # Clear the bit that indicates taht the CalcCRC command is active
        # and all data is processed
        CRCIRq = 0x04
        self.__MFRC522_clearBitMask(self.DIVIRQ_REG, CRCIRq)

        # Immedialty clears the internal FIFO buffer's read and write pointer
        # and ErrorReg register's BufferOvfl bit
        FlushBuffer = 0x80
        self.__MFRC522_setBitMask(self.FIFOLEVEL_REG, FlushBuffer)

        # Write data to FIFO
        i = 0
        while (i < len(data)):
            self.__MFRC522_write(self.FIFODATA_REG, data[i])
            i = i + 1

        # Execute CRC calculation
        self.__MFRC522_write(self.COMMAND_REG, self.MFRC522_CALCCRC)
        i = 255
        while True:
            divirqreg = self.__MFRC522_read(self.DIVIRQ_REG)
            i = i - 1
            if (i == 0):
                # Watchdog expired
                break
            if (divirqreg & CRCIRq):
                # CRC is calculated
                break

        # Retrieve CRC from CRCRESULTREG
        crc = []
        crc.append(self.__MFRC522_read(self.CRCRESULT_LSB_REG))
        crc.append(self.__MFRC522_read(self.CRCRESULT_MSB_REG))

        return (crc)

    def select(self, serialNumber):
        """ Selects a card with a given serial number """
        status = None
        backData = []
        backBits = None

        buffer = []
        buffer.extend(self.MIFARE_SELECTCL1)

        i = 0
        while (i < 5):
            buffer.append(serialNumber[i])
            i = i + 1

        crc = self.__calculateCRC(buffer)
        buffer.extend(crc)

        (status, backData, backBits) = self.__transceiveCard(buffer)

        return (status, backData, backBits)

    def authenticate(self, mode, blockAddr, key, serialNumber):
        """ Authenticates the card """
        status = None
        backData = []
        backBits = None

        buffer = []
        buffer.extend(mode)
        buffer.append(blockAddr)
        buffer.extend(key)

        i = 0
        while (i < 4):
            buffer.append(serialNumber[i])
            i = i + 1

        (status, backData, backBits) = self.__authenticateCard(buffer)

        return (status, backData, backBits)

    def deauthenticate(self):
        """ Deauthenticates the card """
        # Indicates that the MIFARE Crypto1 unit is switched on and
        # therfore all data communication with the card is encrypted
        # Can ONLY be set to logic 1 by a successfull execution of
        # the MFAuthent command
        MFCrypto1On = 0x08
        self.__MFRC522_clearBitMask(self.STATUS2_REG, MFCrypto1On)

    def __authenticateCard(self, data):
        status = None
        backData = []
        backBits = None

        IRqInv = 0x80  # Signal on pin IRQ is inverted
        IdleIEn = 0x10  # Allow the idle interrupt request
        ErrIEn = 0x02  # Allow the error interrupt request
        self.__MFRC522_write(self.COMIEN_REG, (IRqInv | IdleIEn | ErrIEn))

        # Indicates that the bits in the ComIrqReg register are set
        Set1 = 0x80
        self.__MFRC522_clearBitMask(self.COMIRQ_REG, Set1)

        # Immedialty clears the interl FIFO buffer's read and write pointer
        # and ErrorReg register's BufferOvfl bit
        FlushBuffer = 0x80
        self.__MFRC522_setBitMask(self.FIFOLEVEL_REG, FlushBuffer)

        # Cancel running commands
        self.__MFRC522_write(self.COMMAND_REG, self.MFRC522_IDLE)

        # Write data in FIFO register
        i = 0
        while (i < len(data)):
            self.__MFRC522_write(self.FIFODATA_REG, data[i])
            i = i + 1

        # This command manages MIFARE authentication to anable a secure
        # communication to any MIFARE card
        self.__MFRC522_write(self.COMMAND_REG, self.MFRC522_MFAUTHENT)

        # The timer has decrement the value in TCounterValReg register to zero
        TimerIRq = 0x01
        # The receiver has detected the end of a valid data stream
        RxIRq = 0x20
        # A command was terminated or unknown command is started
        IdleIRq = 0x10

        # Wait for an interrupt
        i = 2000
        while True:
            comIRqReg = self.__MFRC522_read(self.COMIRQ_REG)
            if (comIRqReg & TimerIRq):
                # Timeout
                break
            if (comIRqReg & RxIRq):
                # Valid data available in FIFO
                break
            if (comIRqReg & IdleIRq):
                # Command terminate
                break
            if (i == 0):
                # Watchdog expired
                break
            i -= 1

        # Clear the StartSend bit in BitFramingReg register
        StartSend = 0x80
        self.__MFRC522_clearBitMask(self.BITFRAMING_REG, StartSend)

        # Retrieve data from FIFODATAREG
        if (i != 0):
            # The host or a MFRC522's internal state machine tries to write
            # data to the FIFO buffer even though it is already full
            BufferOvfl = 0x10
            # A bit collision is detected
            ColErr = 0x08
            # Parity check failed
            ParityErr = 0x02
            # Set to logic 1 if the SOF is incorrect
            ProtocolErr = 0x01

            errorTest = (BufferOvfl | ColErr | ParityErr | ProtocolErr)
            errorReg = self.__MFRC522_read(self.ERROR_REG)

            # Test if any of the errors above happend
            if (~(errorReg & errorTest)):
                status = self.MIFARE_OK

                # Indicates any error bit in thr ErrorReg register is set
                ErrIRq = 0x02

                # Test if the timer expired and an error occured
                if (comIRqReg & TimerIRq & ErrIRq):
                    status = self.MIFARE_NOTAGERR

            else:
                status = self.MIFARE_ERR

        return (status, backData, backBits)

    def read(self, blockAddr):
        """ Reads data from the card """
        status = None
        backData = []
        backBits = None

        buffer = []
        buffer.extend(self.MIFARE_READ)
        buffer.append(blockAddr)

        crc = self.__calculateCRC(buffer)
        buffer.extend(crc)

        (status, backData, backBits) = self.__transceiveCard(buffer)

        return (status, backData, backBits)

    def write(self, blockAddr, data):
        """ Writes data to the card """
        status = None
        backData = []
        backBits = None

        buffer = []
        buffer.extend(self.MIFARE_WRITE)
        buffer.append(blockAddr)

        crc = self.__calculateCRC(buffer)
        buffer.extend(crc)

        (status, backData, backBits) = self.__transceiveCard(buffer)

        if (status == self.MIFARE_OK):

            buffer.clear()
            buffer.extend(data)

            crc = self.__calculateCRC(buffer)
            buffer.extend(crc)

            (status, backData, backBits) = self.__transceiveCard(buffer)

        return (status, backData, backBits)

    def __MFRC522_antennaOn(self):
        """ Activates the reader/writer antenna """
        value = self.__MFRC522_read(self.TXCONTROL_REG)
        if (~(value & 0x03)):
            self.__MFRC522_setBitMask(self.TXCONTROL_REG, 0x03)

    def __MFRC522_antennaOff(self):
        """ Deactivates the reader/writer antenna """
        self.__MFRC522_clearBitMask(self.TXCONTROL_REG, 0x03)

    def __MFRC522_reset(self):
        """ Resets the reader/writer """
        self.__MFRC522_write(self.COMMAND_REG, self.MFRC522_SOFTRESET)

    def __MFRC522_init(self):
        """ Initialization sequence"""
        self.__MFRC522_reset()

        # Timer starts automatically at the end of the transmission in all
        # communication modes and speeds
        TAuto = 0x80
        # Defines the higher 4 bits of the TPrescaler value
        TPrescaler_Hi = 0x0D
        # Defines the lower 4 bits of the TPrescaler value
        TPrescaler_Lo = 0x3E
        self.__MFRC522_write(self.TMODE_REG, (TAuto | TPrescaler_Hi))
        self.__MFRC522_write(self.TPRESCALER_REG, TPrescaler_Lo)

        # Defines the higher 8 bits of the timer reload value
        TReloadVal_Hi = 0x1E
        # Defines the lower 8 bits of the timer reload value
        TReloadVal_Lo = 0x00
        self.__MFRC522_write(self.TRELOAD_H_REG, TReloadVal_Hi)
        self.__MFRC522_write(self.TRELOAD_L_REG, TReloadVal_Lo)

        Force100ASK = 0x40  # Forces a 100% ASK modulation
        self.__MFRC522_write(self.TXASKREG, Force100ASK)

        # Moderegister reset value
        ResetVal = 0x3F
        # Moderegister feature mask
        FeatureMask = 0x14
        # Transmitter can only be started if RF field is generated
        TxWaitRF = 0x20
        # Defines polarity of pin MFIN, polarity of pin is active HIGH
        PolMFin = 0x08
        # Defines the preset value for the CRC coprocessor for the CalcCRC
        # command
        CRCPreset = 0x01
        self.__MFRC522_write(self.MODE_REG, ((ResetVal &
                                             FeatureMask) |
                                            TxWaitRF |
                                            PolMFin |
                                            CRCPreset))

        # Activate antenna
        self.__MFRC522_antennaOn()

    def __MFRC522_read(self, address):
        """ Read data from an address on the i2c bus """
        #value = self.i2cBus.read_byte_data(self.i2cAddress, address)
        value = self.i2c_bus.readfrom_mem(self.i2c_addr, address, 1)[0]
        return value

    def __MFRC522_write(self, address, value):
        """ Write data on an address on the i2c bus """
        #self.i2cBus.write_byte_data(self.i2cAddress, address, value)
        #print(f'to 0x{self.i2cAddress:x} @{address}={value}')
        self.i2c_bus.writeto_mem(self.i2c_addr, address, bytes([value]))

    def __MFRC522_setBitMask(self, address, mask):
        """ Set bits according to a mask on a address on the i2c bus """
        value = self.__MFRC522_read(address)
        self.__MFRC522_write(address, value | mask)

    def __MFRC522_clearBitMask(self, address, mask):
        """ Resets bits according to a mask on a address on the i2c bus """
        value = self.__MFRC522_read(address)
        self.__MFRC522_write(address, value & (~mask))


# main program
if __name__ == '__main__':
    # init (ws1850s chip have a max freq of 100khz on I2C interface)
    i2c = I2C(id=0, sda=Pin(4), scl=Pin(5), freq=100_000)
    MFRC522Reader = MFRC522(bus=i2c, addr=0x28)

    # read version
    version = MFRC522Reader.get_reader_version()
    print(f'MFRC522 software version: 0x{version:x}')

    # main scan loop
    while True:
        # scan for cards
        (status, backData, tagType) = MFRC522Reader.scan()

        # debug
        print(f'{status=}, {backData=}, {tagType=}')

        if status == MFRC522Reader.MIFARE_OK:
            print(f'Card detected, Type: {tagType}')

            # get UID of the card
            (status, uid, backBits) = MFRC522Reader.identify()
            if status == MFRC522Reader.MIFARE_OK:
                print('Card identified, UID: ', end='')
                for i in range(0, len(uid) - 1):
                    print(f'{uid[i]:02x}:', end='')
                print(f'{uid[len(uid) - 1]:02x}')

                # select the scanned card
                (status, backData, backBits) = MFRC522Reader.select(uid)
                if status == MFRC522Reader.MIFARE_OK:
                    print('Card selected')

                    # TODO: Determine 1K or 4K

                    # authenticate
                    blockAddr = 8
                    (status, backData, backBits) = MFRC522Reader.authenticate(
                        MFRC522Reader.MIFARE_AUTHKEY1,
                        blockAddr,
                        MFRC522Reader.MIFARE_KEY,
                        uid)
                    if (status == MFRC522Reader.MIFARE_OK):
                        print('Card authenticated')

                        # read data from card
                        (status, backData, backBits) = MFRC522Reader.read(blockAddr)
                        if (status == MFRC522Reader.MIFARE_OK):
                            print(f'Block {blockAddr:02} : ', end='')
                            for i in range(0, len(backData)):
                                print(f'{backData[i]:02x} ', end='')
                            print('read')
                        else:
                            print('Error while reading')

                        # deauthenticate
                        MFRC522Reader.deauthenticate()
                        print('Card deauthenticated')
                    else:
                        print('Authentication error')
