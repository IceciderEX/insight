# -*- encoding:utf-8 -*-
import hashlib
import hmac
import base64
import os
from socket import *
import json, time, threading
from websocket import create_connection
from urllib.parse import quote
import logging
import pyaudio

class Client:
    def __init__(self):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (app_id + ts).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding='utf-8')

        apiKey = api_key.encode('utf-8')
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, 'utf-8')
        self.end_tag = "{\"end\": true}"

        self.ws = create_connection(base_url + "?appid=" + app_id + "&ts=" + ts + "&signa=" + quote(signa))
        self.trecv = threading.Thread(target=self.recv)
        self.full_transcription = []  # 存储完整转录结果
        self.is_recording = True  # 控制录音流是否继续
        self.trecv.start()

    def send_audio_stream(self):
        # 使用 pyaudio 获取麦克风音频数据
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        frames_per_buffer=1280)

        try:
            while self.is_recording:
                audio_data = stream.read(1280, exception_on_overflow=False)
                self.ws.send(audio_data)
                time.sleep(0.04)
        except KeyboardInterrupt:
            print("录音停止。")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        self.ws.send(bytes(self.end_tag.encode('utf-8')))
        print("发送结束标志成功。")
        return " ".join(self.full_transcription)

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("接收结果结束")
                    break
                result_dict = json.loads(result)
                if result_dict["action"] == "started":
                    print("握手成功, 结果: " + result)
                if result_dict["action"] == "result":
                    self.process_result(result_dict["data"])
                if result_dict["action"] == "error":
                    print("实时语音识别错误: " + result)
                    self.ws.close()
                    return
        except Exception as e:
            print(f"接收数据时出错: {e}")

    def process_result(self, data):
        """解析返回的数据并处理转写结果"""
        try:
            result_data = json.loads(data)
            words = result_data.get("cn", {}).get("st", {}).get("rt", [])
            for segment in words:
                for word in segment.get("ws", []):
                    recognized_text = word.get("cw", [{}])[0].get("w", "")
                    self.full_transcription.append(recognized_text)  # 保存转录结果
                    print(recognized_text, end="", flush=True)  # 实时打印转录结果
        except Exception as e:
            print(f"解析数据时出错: {e}")

    def close(self):
        self.is_recording = False  # 停止录音流
        self.ws.close()
        print("连接已关闭")


if __name__ == '__main__':
    logging.basicConfig()

    app_id = os.getenv('XUNFEI_APP_ID')
    api_key = os.getenv('XUNFEI_API_KEY')

    client = Client()
    print("按 Ctrl+C 停止录音。")
    try:
        client.send_audio_stream()
    except KeyboardInterrupt:
        pass
    finally:
        client.close()

# import pyaudio
# import requests
# import json
# import struct
# # from text_to_speech import speak
# import random

# # 替换为百度语音的 App Key 和 Secret Key
# BAIDU_API_KEY = "百度API Key"
# BAIDU_SECRET_KEY = "百度Secret Key"
# ACCESS_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
# SPEECH_RECOGNITION_URL = "https://vop.baidu.com/server_api"

# # 随机提示语句
# listening_phrases = [
#     "Yes, how can I assist?",
#     "I'm here, what do you need?",
#     "Listening, go ahead!",
#     "How can I help you today?",
#     "I'm ready, what's up?",
#     "What can I do for you?",
#     "Go ahead, I'm all ears!",
#     "Ready when you are!",
#     "Yes, what would you like?",
#     "How may I assist you today?"
# ]

# # 获取百度 API 的 Access Token
# def get_baidu_access_token():
#     params = {
#         "grant_type": "client_credentials",
#         "client_id": BAIDU_API_KEY,
#         "client_secret": BAIDU_SECRET_KEY
#     }
#     response = requests.post(ACCESS_TOKEN_URL, params=params)
#     if response.status_code == 200:
#         return response.json().get("access_token")
#     else:
#         raise Exception("Failed to get access token from Baidu API")

# # 实时录音并返回 PCM 数据
# def record_audio_stream(duration=5, sample_rate=16000):
#     pa = pyaudio.PyAudio()
#     stream = pa.open(format=pyaudio.paInt16,
#                      channels=1,
#                      rate=sample_rate,
#                      input=True,
#                      frames_per_buffer=1024)
#     print("Recording...")
#     frames = []

#     for _ in range(0, int(sample_rate / 1024 * duration)):
#         data = stream.read(1024)
#         frames.append(data)

#     print("Recording finished.")
#     stream.stop_stream()
#     stream.close()
#     pa.terminate()

#     # 将数据合并为 PCM 格式的字节流
#     return b"".join(frames)

# # 调用百度语音识别 API
# def recognize_speech_baidu(audio_data, access_token):
#     headers = {"Content-Type": "audio/pcm;rate=16000"}
#     params = {
#         "format": "pcm",
#         "rate": 16000,
#         "dev_pid": 1537,  # 普通话识别模型
#         "cuid": "123456PYTHON",
#         "token": access_token
#     }
#     response = requests.post(SPEECH_RECOGNITION_URL, params=params, headers=headers, data=audio_data)
#     if response.status_code == 200:
#         result = response.json()
#         if result.get("err_no") == 0:
#             return result.get("result")[0]
#         else:
#             raise Exception(f"Recognition failed: {result.get('err_msg')}")
#     else:
#         raise Exception("Failed to call Baidu API")

# # 主函数
# def recognize_speech():
#     access_token = get_baidu_access_token()
#     # speak(random.choice(listening_phrases))
#     try:
#         audio_data = record_audio_stream(duration=5)  # 实时录音，返回 PCM 数据
#         transcript = recognize_speech_baidu(audio_data, access_token)
#         print(f"Recognized: {transcript}")
#         return transcript
#     except Exception as e:
#         print(f"An error occurred: {e}")

# if __name__ == "__main__":
#     recognize_speech()
