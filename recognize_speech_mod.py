import pyaudio
import requests
import json
import struct
from text_to_speech import speak
import random

# 替换为百度语音的 App Key 和 Secret Key
BAIDU_API_KEY = "百度API Key"
BAIDU_SECRET_KEY = "百度Secret Key"
ACCESS_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
SPEECH_RECOGNITION_URL = "https://vop.baidu.com/server_api"

# 随机提示语句
listening_phrases = [
    "Yes, how can I assist?",
    "I'm here, what do you need?",
    "Listening, go ahead!",
    "How can I help you today?",
    "I'm ready, what's up?",
    "What can I do for you?",
    "Go ahead, I'm all ears!",
    "Ready when you are!",
    "Yes, what would you like?",
    "How may I assist you today?"
]

# 获取百度 API 的 Access Token
def get_baidu_access_token():
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }
    response = requests.post(ACCESS_TOKEN_URL, params=params)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception("Failed to get access token from Baidu API")

# 实时录音并返回 PCM 数据
def record_audio_stream(duration=5, sample_rate=16000):
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=sample_rate,
                     input=True,
                     frames_per_buffer=1024)
    print("Recording...")
    frames = []

    for _ in range(0, int(sample_rate / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)

    print("Recording finished.")
    stream.stop_stream()
    stream.close()
    pa.terminate()

    # 将数据合并为 PCM 格式的字节流
    return b"".join(frames)

# 调用百度语音识别 API
def recognize_speech_baidu(audio_data, access_token):
    headers = {"Content-Type": "audio/pcm;rate=16000"}
    params = {
        "format": "pcm",
        "rate": 16000,
        "dev_pid": 1537,  # 普通话识别模型
        "cuid": "123456PYTHON",
        "token": access_token
    }
    response = requests.post(SPEECH_RECOGNITION_URL, params=params, headers=headers, data=audio_data)
    if response.status_code == 200:
        result = response.json()
        if result.get("err_no") == 0:
            return result.get("result")[0]
        else:
            raise Exception(f"Recognition failed: {result.get('err_msg')}")
    else:
        raise Exception("Failed to call Baidu API")

# 主函数
def recognize_speech():
    access_token = get_baidu_access_token()
    speak(random.choice(listening_phrases))
    try:
        audio_data = record_audio_stream(duration=5)  # 实时录音，返回 PCM 数据
        transcript = recognize_speech_baidu(audio_data, access_token)
        print(f"Recognized: {transcript}")
        return transcript
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    recognize_speech()
