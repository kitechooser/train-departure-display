import sys
import argparse
import os
import time
import pygame
from gtts import gTTS
import numpy as np
import soundfile as sf
import sounddevice as sd
import io
import tempfile

class AudioAnnouncement:
    def __init__(self, volume=0.9, echo_enabled=True, echo_delay=0.3, echo_decay=0.5, num_echoes=3):
        pygame.mixer.init()
        pygame.mixer.music.set_volume(volume)
        self.temp_file = 'announcement.mp3'
        self.echo_enabled = echo_enabled
        self.echo_delay = echo_delay
        self.echo_decay = echo_decay
        self.num_echoes = num_echoes
        
    def create_speech_with_echo(self, text, output_file):
        """Creates TTS audio with echo/reverb effect"""
        # Generate TTS audio
        tts = gTTS(text=text, lang='en-gb')
        
        # Save to a bytes buffer
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # Convert to WAV using scipy
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_mp3:
            temp_mp3.write(mp3_fp.read())
            temp_mp3.flush()

            # Read the audio data
            data, sample_rate = sf.read(temp_mp3.name)

        # Convert to float32 for processing
        samples = data.astype(np.float32)

        if self.echo_enabled:
            # Calculate delay in samples
            delay_samples = int(self.echo_delay * sample_rate)

            # Create output buffer
            total_length = len(samples) + (delay_samples * self.num_echoes)
            output = np.zeros(total_length, dtype=np.float32)

            # Add original audio
            output[:len(samples)] += samples

            # Add echoes
            for i in range(self.num_echoes):
                echo_start = (i + 1) * delay_samples
                echo_end = echo_start + len(samples)
                echo_volume = self.echo_decay ** (i + 1)
                output[echo_start:echo_end] += samples * echo_volume

            # Normalize to prevent clipping
            max_amplitude = np.max(np.abs(output))
            if max_amplitude > 1.0:
                output /= max_amplitude
        else:
            output = samples

        # Save the final audio
        sf.write(output_file, output, sample_rate)

    def speak(self, text):
        try:
            # Create audio with echo effect
            self.create_speech_with_echo(text, self.temp_file)
            
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

def speak(text, rate=None, volume=0.9, driver=None, device=None, voice=None, 
          echo_enabled=True, echo_delay=0.3, echo_decay=0.5, num_echoes=3):
    """Speak text using gTTS"""
    announcer = AudioAnnouncement(volume, echo_enabled, echo_delay, echo_decay, num_echoes)
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
    parser.add_argument('--echo-enabled', type=bool, default=True, help='Enable echo effect')
    parser.add_argument('--echo-delay', type=float, default=0.3, help='Delay between echoes in seconds')
    parser.add_argument('--echo-decay', type=float, default=0.5, help='Volume reduction for each echo (0-1)')
    parser.add_argument('--num-echoes', type=int, default=3, help='Number of echo repetitions')
    
    args = parser.parse_args()
    
    try:
        speak(
            args.message,
            rate=args.rate,
            volume=args.volume,
            driver=args.driver,
            device=args.device,
            voice=args.voice,
            echo_enabled=args.echo_enabled,
            echo_delay=args.echo_delay,
            echo_decay=args.echo_decay,
            num_echoes=args.num_echoes
        )
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
