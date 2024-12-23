import cv2
from time import sleep
from text_to_speech_mod import speak

def take_picture(filepath: str):
    """Take a picture using the specified camera and save it to the provided file path."""
    speak("Alright, I'm taking a picture now.")
    print("Taking picture...")
    cap = cv2.VideoCapture(0)
    sleep(2)
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        cap.release()
        return None

    cv2.imwrite(filepath, frame)
    print(f"Picture taken and saved as {filepath}")
    cap.release()
    speak("Got it! I've taken picture and saved it.")
    return f"Picture taken and saved as {filepath}"