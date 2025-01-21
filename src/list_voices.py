import pyttsx3

engine = pyttsx3.init('nsss')
voices = engine.getProperty('voices')

print("Available voices:")
for voice in voices:
    print(f"ID: {voice.id}")
    print(f"Name: {voice.name}")
    print(f"Languages: {voice.languages}")
    print(f"Gender: {voice.gender}")
    print("---")
