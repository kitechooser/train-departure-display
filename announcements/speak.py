import sys
import argparse
import platform
import pyttsx3

def get_driver(driver_name):
    """Get the appropriate TTS driver based on platform and settings"""
    if driver_name == "auto":
        # Auto-detect platform
        if platform.system() == "Darwin":
            return "nsss"
        elif platform.system() == "Linux":
            return "espeak"
        else:
            return None
    return driver_name

def speak(text, rate=130, volume=0.9, driver="auto", device="default", voice=None):
    """Speak text using the specified driver and settings"""
    # Get appropriate driver
    driver_name = get_driver(driver)
    
    # Initialize engine with driver
    engine = pyttsx3.init(driver_name)
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)
    
    # Set voice if specified, otherwise try to find an English voice
    if voice:
        engine.setProperty('voice', voice)
    else:
        voices = engine.getProperty('voices')
        if voices:
            for v in voices:
                if 'en' in getattr(v, 'languages', [''])[0].lower():
                    engine.setProperty('voice', v.id)
                    break
    
    # On Linux/Pi, set the audio device if specified
    if platform.system() == "Linux" and device != "default":
        engine.setProperty('device', device)
    
    try:
        engine.say(text)
        engine.runAndWait()
    finally:
        engine.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Text-to-speech announcement')
    parser.add_argument('message', help='The message to speak')
    parser.add_argument('--rate', type=int, default=150, help='Speech rate (words per minute)')
    parser.add_argument('--volume', type=float, default=0.9, help='Volume (0.0-1.0)')
    parser.add_argument('--driver', default='auto', help='TTS driver (auto, nsss, espeak)')
    parser.add_argument('--device', default='default', help='Audio device (Linux/Pi only)')
    parser.add_argument('--voice', help='Voice ID to use')
    
    args = parser.parse_args()
    
    try:
        speak(
            args.message,
            rate=args.rate,
            volume=args.volume,
            driver=args.driver,
            device=args.device,
            voice=args.voice
        )
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
