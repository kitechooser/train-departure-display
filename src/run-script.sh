#!/bin/bash

# API Key (required)
export apiKey="9dc15c51-f949-470a-8319-35f6a75f7271"

# Add project root to Python path
export PYTHONPATH="$PYTHONPATH:$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"

# Run the script
python main.py
