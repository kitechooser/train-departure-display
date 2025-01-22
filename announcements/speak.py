import sys
import argparse
import os
import time
import pygame
from gtts import gTTS

class AudioAnnouncement:
    def __init__(self, volume=0.9):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(volume)
        self.temp_file = 'announcement.mp3'
        
    def speak(self, text):
        try:
            # Create gTTS instance and generate audio
            tts = gTTS(text=text, lang='en-gb')
            
            # Save to temporary file
            tts.save(self.temp_file)
            
            # Play the audio
            pygame.mixer.music.load(self.temp_file)
            pygame.mixer.music.play()
            
            # Wait for audio to finish
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
                
            # Clean up
            pygame.mixer.music.unload()
            os.remove(self.temp_file)
            
        except Exception as e:
            print(f"Error playing announcement: {str(e)}", file=sys.stderr)
            
    def cleanup(self):
        """Clean up any temporary files"""
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass

def speak(text, rate=None, volume=0.9, driver=None, device=None, voice=None):
    """Speak text using gTTS"""
    announcer = AudioAnnouncement(volume)
    try:
        announcer.speak(text)
    finally:
        announcer.cleanup()

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
