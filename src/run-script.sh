#!/bin/bash

# Display Settings
export targetFPS=70
export refreshTime=180
export fpsTime=180
export screenRotation=2
export screenBlankHours=""  # Format: "23-5" for 11PM-5AM
export dualScreen=True
export previewMode=True

# Debug Settings
export debug=False
export headless=False

# National Rail Settings
export apiKey="9dc15c51-f949-470a-8319-35f6a75f7271"
export departureStation="PAD"  # e.g., PAD for Paddington
export destinationStation=""   # Leave empty for all destinations
export screen1Platform=""      # Leave empty for all platforms
export firstDepartureBold=True
export showDepartureNumbers=True

# TfL Settings
export tflEnabled=True
export tflAppId="DepartureBoard"
export tflAppKey="a432a817f61d4a65ba62e226e48e665b"
export tflDirection="inbound"  # inbound or outbound
export tflRefreshTime=90
export tflMode="tube"         # tube, dlr, etc.

# Screen 2 Settings (if dualScreen=True)
export screen2DepartureStation="VIC"  # e.g., VIC for Victoria
export screen2DestinationStation=""   # Leave empty for all destinations
export screen2Platform=""             # Leave empty for all platforms
export screen2Mode="tfl"              # rail or tfl

# Operating Hours
export operatingHours="5-23"  # Format: "5-23" for 5AM-11PM
export timeOffset="0"         # Offset in minutes

# Station Name Customization
export outOfHoursName="London Paddington"
export individualStationDepartureTime=False

# Run the script
python main.py