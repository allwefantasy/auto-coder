  
import io

def play_mp3(path):
    try:
        import pygame
    except ImportError:
        raise ImportError("The pygame module is required to play audio files. Try running 'pip install pygame'")
    # Initialize the mixer module
    pygame.mixer.init()

    # Load the MP3 file
    pygame.mixer.music.load(path)

    # Start playing the music
    pygame.mixer.music.play()

    # Wait for the music to finish playing
    while pygame.mixer.music.get_busy():
        time.sleep(1)


def play_wave(filename:str):
    try:
        import simpleaudio as sa
    except ImportError:
        raise ImportError("The simpleaudio module is required to play audio files. Try running 'pip install simpleaudio'")  
    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()

