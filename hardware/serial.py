
from serial.tools import list_ports


class ConnectionManager:

    @staticmethod
    def find_esp32():
        for port in list_ports.comports():
            description = (
                f"{port.description} {port.manufacturer or ''}"
            ).upper()

            keywords = [
                "ESP32",
                "CP210",
                "CH340",
                "USB JTAG/SERIAL",
                "FTDI",
                "ESPRESSIF",
            ]

            if any(keyword in description for keyword in keywords):
                return {
                    "connected": True,
                    "port": port.device,
                    "description": port.description,
                }

        return {
            "connected": False,
            "port": None,
            "description": "ESP32 bulunamadı",
        }
