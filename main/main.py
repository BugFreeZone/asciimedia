import cv2
import os
import sys
import subprocess
import threading
import wave
import pyaudio
import numpy as np
from queue import Queue

TERMINAL_WIDTH, TERMINAL_HEIGHT = 80, 24
ASCII_CHARS = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
PLAYER_WIDTH = 50

def init_terminal():
    """Инициализация размера терминала"""
    try:
        global TERMINAL_WIDTH, TERMINAL_HEIGHT
        TERMINAL_WIDTH, TERMINAL_HEIGHT = os.get_terminal_size()
        TERMINAL_HEIGHT = max(TERMINAL_HEIGHT, 10)
    except:
        pass

def resize_image(img, new_width=TERMINAL_WIDTH):
    """Улучшенное масштабирование с сохранением деталей"""
    height, width = img.shape[:2]
    aspect_ratio = height/width
    
    new_height = int(new_width * aspect_ratio * 0.5)
    
    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    resized = cv2.GaussianBlur(resized, (3, 3), 0)
    return resized

def image_to_ascii(img, width=TERMINAL_WIDTH):
    """Улучшенная конвертация в ASCII с сохранением деталей"""
    if len(img.shape) == 3:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        gray = lab[:,:,0]
        color_resized = resize_image(img, width)
    else:
        gray = img
        color_resized = None
    
    resized = resize_image(gray, width)
    
    alpha = 1.5
    resized = cv2.convertScaleAbs(resized, alpha=alpha, beta=0)
    
    ascii_art = ""
    for y in range(resized.shape[0]):
        for x in range(resized.shape[1]):
            pixel = resized[y,x]
            gamma = 0.6
            normalized = (pixel / 255) ** gamma
            char_index = int(normalized * (len(ASCII_CHARS) - 1))
            
            if color_resized is not None:
                b, g, r = color_resized[y,x]
                r = min(int(r * 1.2), 255)
                g = min(int(g * 1.1), 255)
                b = min(int(b * 1.1), 255)
                color_code = f"\033[38;2;{r};{g};{b}m"
                ascii_art += f"{color_code}{ASCII_CHARS[char_index]}"
            else:
                ascii_art += ASCII_CHARS[char_index]
        ascii_art += "\033[0m\n"
    return ascii_art

def extract_audio(video_path, audio_path="temp_audio.wav"):
    """Извлечение аудио из видео с помощью ffmpeg"""
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            "-y", audio_path,
            "-loglevel", "quiet"
        ]
        
        subprocess.run(cmd, check=True)
        return audio_path
    except:
        return None

def play_audio(audio_path, volume=0.7):
    p=pyaudio.PyAudio()
    exit_flag=False
    wf=wave.open(audio_path, "rb")
    stream=p.open(format=p.get_format_from_width(wf.getsampwidth()),
                  channels=wf.getnchannels(),
                  rate=wf.getframerate(),
                  output=True)
    while not exit_flag:
        data=wf.readframes(1024)
        if data:
            audio_data=np.frombuffer(data, dtype=np.int16)
            audio_data=(audio_data*volume).astype(np.int16)
            stream.write(audio_data.tobytes())
    stream.stop_stream()
    stream.close()
    p.terminate()

def play_video(video_path, width=TERMINAL_WIDTH):
    """Воспроизведение видео с улучшенным ASCII-артом"""
    audio_path = extract_audio(video_path)
    stop_event = threading.Event()
    
    if audio_path:
        audio_thread = threading.Thread(
            target=play_audio,
            args=(audio_path,),
            daemon=True
        )
        audio_thread.start()
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error opening video file")
        stop_event.set()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    delay = 1 / fps if fps > 0 else 0.03
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.detailEnhance(frame, sigma_s=10, sigma_r=0.15)
            ascii_frame = image_to_ascii(frame, width)
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print(ascii_frame, end='', flush=True)
    
    except KeyboardInterrupt:
        print("\nPlayback stopped")
    finally:
        cap.release()
        stop_event.set()
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except:
                pass

def show_image(image_path, width=TERMINAL_WIDTH):
    """Отображение изображения с улучшенным качеством"""
    img = cv2.imread(image_path)
    if img is None:
        print("Error loading image")
        return
    
    img = cv2.detailEnhance(img, sigma_s=10, sigma_r=0.15)
    ascii_art = image_to_ascii(img, width)
    print(ascii_art)
    input("Press Enter to continue...")

def main():
    """Основная функция"""
    init_terminal()
    
    if len(sys.argv) < 2:
        print("Usage: python media_player.py <file_path> [width]")
        print("Video example: python media_player.py video.mp4 80")
        print("Image example: python media_player.py image.jpg")
        print("Audio example: python media_player.py audio.wav")
        return
    
    file_path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else TERMINAL_WIDTH
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found")
        return
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.mp4', '.avi', '.mov', '.mkv']:
        play_video(file_path, width)
    elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        show_image(file_path, width)
    else:
        print(f"Unsupported file format: {ext}")

if __name__ == "__main__":
    try:
        import cv2
        import pyaudio
        import numpy as np
    except ImportError:
        print("Required packages: opencv-python, pyaudio, numpy")
        print("Install with: pip install opencv-python pyaudio numpy")
        sys.exit(1)
    
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        print("Warning: ffmpeg not found. Audio in videos won't work.")
    
    main()
