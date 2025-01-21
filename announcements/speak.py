import sys
import argparse
import platform
import os
import time
import pygame
import requests
import base64
import re
from urllib.parse import quote

class GoogleTTS:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_token(self, text):
        # Get token from translate page
        url = "https://translate.google.com/"
        response = self.session.get(url)
        token_pattern = r'"FdrFJe":"([^"]+)"'
        match = re.search(token_pattern, response.text)
        if not match:
            raise ValueError("Could not find token pattern")
        return match.group(1)

    def get_audio(self, text, lang='en-gb'):
        token = self.get_token(text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={quote(text)}&tk={token}"
        response = self.session.get(url)
        if response.status_code != 200:
            raise Exception(f"Failed to get audio: {response.status_code}")
        return response.content

class AudioAnnouncement:
    def __init__(self, volume=0.9):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(volume)
        self.temp_file = 'announcement.mp3'
        self.tts = GoogleTTS()
        
    def speak(self, text):
        try:
            # Get audio data from Google
            audio_data = self.tts.get_audio(text)
            
            # Save to temporary file
            with open(self.temp_file, 'wb') as f:
                f.write(audio_data)
            
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
    """Speak text using platform-specific TTS"""
    system = platform.system()
    
    if system == "Darwin":
        # On macOS, use pyttsx3 with nsss
        try:
            import pyttsx3
            engine = pyttsx3.init("nsss")
            engine.setProperty('volume', volume)
            if voice:
                engine.setProperty('voice', voice)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Error with macOS speech: {str(e)}", file=sys.stderr)
    else:
        # On Linux/Pi, use gTTS
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
