# Charging-Station

📁 Full write-up, photos, and my role: [Portfolio](https://bit.ly/charity-osoro-portfolio)

Team repo (RPI IoT course): [rpi-iot-projects/2026-Team-14-Smart-Charging-Station](https://github.com/rpi-iot-projects/2026-Team-14-Smart-Charging-Station)

To send data manually:
```
mosquitto_pub -h <pi-ip> -t <prefix>/devices/battery/android -m '{"device":"<device>","percent":26,"plugged":false,"timestamp":"04:20:15:50:00"}'
```
