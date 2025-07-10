import cv2
import os
import time
import sys
import subprocess
import threading
import wave
import pyaudio
from queue import Queue

def get_terminal_size():
    try:
        cols, rows = os.get_terminal_size()
        return cols, rows
    except:
        return 80, 24

def resize_image(img, new_width=None):
    if new_width is None:
        new_width, _ = get_terminal_size()
    
    height, width = img.shape[:2]
    aspect_ratio = height/width
    new_height = int(new_width * aspect_ratio * 0.55)
    return cv2.resize(img, (new_width, new_height))

def image_to_ascii(img, width=None):
    chars = "@%#*+=-:. "
    
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        color_resized = resize_image(img, width)
    else:
        gray = img
        color_resized = None
    
    resized = resize_image(gray, width)
    
    ascii_art = ""
    for y in range(resized.shape[0]):
        for x in range(resized.shape[1]):
            brightness = resized[y,x]
            char_index = int(brightness / 255 * (len(chars) - 1))
            
            if color_resized is not None:
                b, g, r = color_resized[y,x]
                color_code = f"\033[38;2;{r};{g};{b}m"
                ascii_art += f"{color_code}{chars[char_index]}"
            else:
                ascii_art += chars[char_index]
        ascii_art += "\033[0m\n"
    
    return ascii_art

def extract_audio(video_path, audio_path="temp_audio.wav"):
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

def play_audio(audio_path, stop_event):
    try:
        if not os.path.exists(audio_path):
            return
        
        wf = wave.open(audio_path, 'rb')
        p = pyaudio.PyAudio()
        
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                      channels=wf.getnchannels(),
                      rate=wf.getframerate(),
                      output=True)
        
        chunk = 1024
        data = wf.readframes(chunk)
        
        while data and not stop_event.is_set():
            stream.write(data)
            data = wf.readframes(chunk)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
    except:
        pass

def play_media(file_path, width=None):
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    is_video = any(file_path.lower().endswith(ext) for ext in video_extensions)
    
    if is_video:
        audio_path = extract_audio(file_path)
        stop_event = threading.Event()
        
        if audio_path:
            audio_thread = threading.Thread(
                target=play_audio,
                args=(audio_path, stop_event),
                daemon=True
            )
            audio_thread.start()
        
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            print("Ошибка открытия видео файла(Error opening the video file)")
            stop_event.set()
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            return
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = 1 / fps if fps > 0 else 0.03
        
        try:
            while True:
                start_time = time.time()
                ret, frame = cap.read()
                if not ret:
                    break
                
                ascii_frame = image_to_ascii(frame, width)
                os.system('cls' if os.name == 'nt' else 'clear')
                print(ascii_frame, end='', flush=True)
                
                elapsed = time.time() - start_time
                if elapsed < delay:
                    time.sleep(delay - elapsed)
        
        except KeyboardInterrupt:
            print("\nВоспроизведение остановлено(Playback is stopped)")
        finally:
            cap.release()
            stop_event.set()
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
    else:
        img = cv2.imread(file_path)
        if img is None:
            print("Ошибка загрузки изображения(Image upload error)")
            return
        
        ascii_art = image_to_ascii(img, width)
        print(ascii_art)

def main():
    if len(sys.argv) < 2:
        print("Использование(Usage): python media_player.py <file_path> [width]")
        print("Пример для видео(Example for a video): python media_player.py video.mp4 80")
        print("Пример для изображения(Example for an image): python media_player.py image.jpg 100")
        return
    
    file_path = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден")
        return
    
    try:
        import cv2
        import pyaudio
    except ImportError:
        print("Требуются библиотеки(Libraries are requiried): opencv-python и pyaudio")
        print("Установите их командой(Install them with the command):")
        print("pip install opencv-python pyaudio")
        return
    
    play_media(file_path, width)

if __name__ == "__main__":
    main()
