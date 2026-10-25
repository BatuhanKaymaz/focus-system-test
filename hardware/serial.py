"""
ESP32 ile seri port üzerinden haberleşme.

PROTOKOL (115200 baud, her mesaj '\\n' ile biter)

PC -> ESP32
    ON            aktüatörü çalıştır
    OFF           aktüatörü kapat
    STOP          acil durdur (her şeyi kapatır)
    CUR:12.5      hedef akım (mA, 4.0 - 20.0)
    MODE:ONOFF    ON/OFF moduna geç
    MODE:PROP     oransal moda geç

ESP32 -> PC
    DATA,tork,akim,gerilim,sicaklik,hiz,pozisyon
    ornek: DATA,1.25,0.80,12.1,35.2,1200,64
    ACK,...       komut alındı (isteğe bağlı)
    ERR,...       hata mesajı
"""

import random

import serial
from serial.tools import list_ports

from PySide6.QtCore import QObject, QTimer, Signal


# True yaparsan gerçek cihaz olmadan sahte verilerle arayüzü test edersin.
# Gerçek cihazla çalışırken MUTLAKA False olmalı.
SIMULATION = False

# True yaparsan gönderilen/alınan her satır konsola yazılır.
DEBUG_LOG = False

BAUD_RATE = 115200

KEYWORDS = (
    "ESP32",
    "CP210",
    "CH340",
    "USB JTAG/SERIAL",
    "FTDI",
    "ESPRESSIF",
)

# DATA satırındaki alanların sırası
DATA_FIELDS = (
    "torque",
    "current",
    "voltage",
    "temperature",
    "speed",
    "position",
)


class ConnectionManager(QObject):
    data_received = Signal(dict)     # {"torque": 1.2, ...}
    line_received = Signal(str)      # DATA dışındaki satırlar (ACK, ERR...)
    connection_lost = Signal()       # okuma/yazma sırasında bağlantı koptu

    def __init__(self, parent=None):
        super().__init__(parent)

        self._serial = None
        self._port_name = ""
        self._buffer = bytearray()

        self._read_timer = QTimer(self)
        self._read_timer.setInterval(20)
        self._read_timer.timeout.connect(self._read_serial)

        # Simülasyon durumu
        self._simulated = False
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(100)
        self._sim_timer.timeout.connect(self._simulation_tick)
        self._sim_reset()

    # -----------------------------------------------------
    # BAĞLANTI
    # -----------------------------------------------------

    @property
    def is_connected(self):
        if self._simulated:
            return True

        return self._serial is not None and self._serial.is_open

    @staticmethod
    def _find_port():
        for port in list_ports.comports():
            description = (
                f"{port.description} {port.manufacturer or ''}"
            ).upper()

            if any(keyword in description for keyword in KEYWORDS):
                return port.device, port.description

        return None

    def ensure_connection(self):
        """
        Bağlıysa durumu döndürür. Bağlı değilse ESP32'yi bulup
        portu açmayı dener. Arayüzdeki zamanlayıcı bunu çağırır.
        """
        if SIMULATION:
            if not self._simulated:
                self._sim_reset()
                self._simulated = True
                self._sim_timer.start()

            return {
                "connected": True,
                "port": "SİMÜLASYON",
                "description": "Sahte cihaz",
            }

        if self.is_connected:
            return {
                "connected": True,
                "port": self._port_name,
                "description": "ESP32 bağlı",
            }

        found = self._find_port()

        if found is None:
            return {
                "connected": False,
                "port": None,
                "description": "ESP32 bulunamadı",
            }

        device, description = found

        try:
            self._open(device)
        except (serial.SerialException, OSError) as error:
            return {
                "connected": False,
                "port": device,
                "description": description,
                "error": str(error),
            }

        return {
            "connected": True,
            "port": device,
            "description": description,
        }

    # Eski isimle de çağrılabilsin
    find_esp32 = ensure_connection

    def _open(self, device):
        port = serial.Serial()
        port.port = device
        port.baudrate = BAUD_RATE
        port.timeout = 0
        port.write_timeout = 0.5

        # Port açılırken ESP32'nin resetlenmesini engellemek için
        port.dtr = False
        port.rts = False

        port.open()

        self._serial = port
        self._port_name = device
        self._buffer.clear()
        self._read_timer.start()

        # Güvenlik: bağlanınca her şeyi kapalı duruma getir
        self.send_command("STOP")

    def close(self):
        self._read_timer.stop()
        self._sim_timer.stop()
        self._simulated = False

        if self._serial is not None:
            try:
                self._serial.close()
            except (serial.SerialException, OSError):
                pass

        self._serial = None
        self._port_name = ""
        self._buffer.clear()

    def _handle_disconnect(self):
        self.close()
        self.connection_lost.emit()

    # -----------------------------------------------------
    # KOMUT GÖNDERME
    # -----------------------------------------------------

    def send_command(self, command):
        if DEBUG_LOG:
            print(f"[TX] {command}")

        if self._simulated:
            self._sim_command(command)
            return True

        if not self.is_connected:
            return False

        try:
            self._serial.write(f"{command}\n".encode("ascii"))
            return True
        except (serial.SerialException, OSError):
            self._handle_disconnect()
            return False

    def send_on(self):
        return self.send_command("ON")

    def send_off(self):
        return self.send_command("OFF")

    def send_stop(self):
        return self.send_command("STOP")

    def send_current(self, milliamps):
        return self.send_command(f"CUR:{milliamps:.1f}")

    def send_mode(self, mode):
        name = "ONOFF" if mode == "onoff" else "PROP"
        return self.send_command(f"MODE:{name}")

    # -----------------------------------------------------
    # VERİ OKUMA
    # -----------------------------------------------------

    def _read_serial(self):
        if self._serial is None or not self._serial.is_open:
            return

        try:
            waiting = self._serial.in_waiting

            if waiting:
                self._buffer.extend(self._serial.read(waiting))
        except (serial.SerialException, OSError):
            self._handle_disconnect()
            return

        # Satır sonu gelmeden buffer şişmesin
        if len(self._buffer) > 4096 and b"\n" not in self._buffer:
            self._buffer.clear()

        while True:
            index = self._buffer.find(b"\n")

            if index < 0:
                break

            raw = bytes(self._buffer[:index])
            del self._buffer[:index + 1]

            line = raw.decode("utf-8", errors="ignore").strip()

            if line:
                self._handle_line(line)

    def _handle_line(self, line):
        if DEBUG_LOG:
            print(f"[RX] {line}")

        if line.startswith("DATA,"):
            values = line.split(",")[1:]
            data = {}

            for key, text in zip(DATA_FIELDS, values):
                try:
                    data[key] = float(text)
                except ValueError:
                    continue

            if data:
                self.data_received.emit(data)
        else:
            self.line_received.emit(line)

    # -----------------------------------------------------
    # SİMÜLASYON (cihaz olmadan test için)
    # -----------------------------------------------------

    def _sim_reset(self):
        self._sim_running = False
        self._sim_position = 0.0
        self._sim_target = 0.0
        self._sim_temperature = 25.0

    def _sim_command(self, command):
        if command == "ON":
            self._sim_running = True
            self._sim_target = 100.0
        elif command == "OFF":
            self._sim_running = False
            self._sim_target = 0.0
        elif command == "STOP":
            self._sim_running = False
            self._sim_target = self._sim_position
        elif command.startswith("CUR:"):
            try:
                milliamps = float(command[4:])
            except ValueError:
                self.line_received.emit("ERR,BAD_VALUE")
                return

            if not 4.0 <= milliamps <= 20.0:
                self.line_received.emit("ERR,CUR_RANGE")
                return

            self._sim_running = True
            self._sim_target = (milliamps - 4.0) / 16.0 * 100.0
        elif command.startswith("MODE:"):
            self._sim_running = False
            self._sim_target = self._sim_position

    def _simulation_tick(self):
        step = 4.0
        difference = self._sim_target - self._sim_position

        if abs(difference) <= step:
            self._sim_position = self._sim_target
            moving = False
        else:
            self._sim_position += step if difference > 0 else -step
            moving = True

        active = self._sim_running or moving

        if active:
            self._sim_temperature = min(
                90.0, self._sim_temperature + 0.05
            )
        else:
            self._sim_temperature = max(
                25.0, self._sim_temperature - 0.02
            )

        noise = random.uniform

        self.data_received.emit({
            "torque": (
                1.0 + 0.04 * self._sim_position + noise(-0.05, 0.05)
                if active else 0.0
            ),
            "current": (
                0.5 + 0.01 * self._sim_position + noise(-0.02, 0.02)
                if active else 0.0
            ),
            "voltage": 24.0 + noise(-0.1, 0.1),
            "temperature": self._sim_temperature,
            "speed": 1200.0 + noise(-20, 20) if moving else 0.0,
            "position": self._sim_position,
        })