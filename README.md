# Charging-Station

📁 Full write-up, photos, and my role: [Portfolio](https://bit.ly/charity-osoro-portfolio)

To send data manually:
```
mosquitto_pub -h <pi-ip> -t <prefix>/devices/battery/android -m '{"device":"<device>","percent":26,"plugged":false,"timestamp":"04:20:15:50:00"}'
```
