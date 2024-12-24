import wake_word_detection
import recognize_speech_mod
from service_mod import get_response
from text_to_speech_mod import speak


def main():
    while True:
        detector = wake_word_detection.Client()
        try:
            detector.send_audio_stream()
        except KeyboardInterrupt:
            print("Stopped by user.")
        finally:
            detector.close()

        if detector.wake_word_detected:
                print("Wake word detected!")
                print("Trying to recognize speech...")
                recognizer = recognize_speech_mod.Client()
                user_input = recognizer.send_audio_stream()
                recognizer.close()
                if user_input:
                    print(f"User's input: {user_input}")
                    response = get_response(user_input)
                    speak(response)


if __name__ == "__main__":
    main()
