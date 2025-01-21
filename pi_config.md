

Screen Connections:
| Purpose | OLED PIN | Screen 1 Pi PIN | Screen 2 Pi PIN | Notes |
|---------|----------|-----------------|-----------------|--------|
| Ground | PIN.1 (VSS) | PIN 9 (GND) | PIN 14 (GND) | |
| Power | PIN.2 (VBAT) | PIN 1 (3.3V) | PIN 4 (3.3V) | |
| SCLK | PIN.4 | PIN 23 (GPIO11) | PIN 40 (GPIO21) | SPI0_SCLK for Screen 1, SPI1_SCLK for Screen 2 |
| MOSI | PIN.5 | PIN 19 (GPIO10) | PIN 38 (GPIO20) | SPI0_MOSI for Screen 1, SPI1_MOSI for Screen 2 |
| DC | PIN.14 | PIN 18 (GPIO24) | PIN 13 (GPIO27) | Data/Command pin |
| Reset | PIN.15 | PIN 22 (GPIO25) | PIN 31 (GPIO31) | Reset pin |
| CE | PIN.16 | PIN 24 (CE0) | PIN 12 (GPIO18) | Chip Enable |

Both screens share the same config.txt structure but use different SPI buses and GPIO pins:
```
# Screen 1
dtoverlay=ssd1322,spi0-0cs,dc_pin=24,reset_pin=25

# Screen 2
dtoverlay=ssd1322-spi1,dc_pin=27,reset_pin=31
gpio=27,31=op
```