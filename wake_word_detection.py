# -*- encoding:utf-8 -*-
import hashlib
import hmac
import base64
import os
import json
import time
import threading
from websocket import create_connection
from urllib.parse import quote
import logging
import pyaudio


app_id = os.getenv("XUNFEI_APP_ID")
api_key = os.getenv("XUNFEI_API_KEY")

class Client:
    def __init__(self):
        base_url = "ws://rtasr.xfyun.cn/v1/ws"
        ts = str(int(time.time()))
        tt = (app_id + ts).encode("utf-8")
        md5 = hashlib.md5()
        md5.update(tt)
        baseString = md5.hexdigest()
        baseString = bytes(baseString, encoding="utf-8")

        apiKey = api_key.encode("utf-8")
        signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
        signa = base64.b64encode(signa)
        signa = str(signa, "utf-8")
        self.end_tag = '{"end": true}'

        self.ws = create_connection(
            base_url + "?appid=" + app_id + "&ts=" + ts + "&signa=" + quote(signa)
        )
        self.buffer = ""  # 用于拼接识别结果的缓冲区
        self.wake_word_detected = False  # 唤醒词检测标志
        self.trecv = threading.Thread(target=self.recv)
        self.is_recording = True  # 录音状态标志
        self.trecv.start()

    def send_audio_stream(self):
        """使用 pyaudio 捕获麦克风音频并发送到服务端"""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1280,
        )

        print("Listening for wake word...")

        try:
            while not self.wake_word_detected and self.is_recording:
                audio_data = stream.read(1280, exception_on_overflow=False)
                self.ws.send(audio_data)
                time.sleep(0.04)  # 确保按服务端要求的速率发送数据
        except KeyboardInterrupt:
            print("Audio stream stopped.")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        # 发送结束标志
        self.ws.send(bytes(self.end_tag.encode("utf-8")))
        print("Sent end tag.")

    def recv(self):
        """接收服务端返回数据并检测唤醒词"""
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("Receive result end.")
                    break
                result_dict = json.loads(result)
                if result_dict["action"] == "started":
                    print("Handshake success, result: " + result)
                elif result_dict["action"] == "result":
                    self.process_result(result_dict["data"])
                elif result_dict["action"] == "error":
                    print("RTASR error: " + result)
                    self.ws.close()
                    break
        except Exception as e:
            print(f"Error receiving data: {e}")

    def process_result(self, data):
        """解析返回的数据并检测唤醒词"""
        try:
            result_data = json.loads(data)
            words = result_data.get("cn", {}).get("st", {}).get("rt", [])
            for segment in words:
                for word in segment.get("ws", []):
                    recognized_text = word.get("cw", [{}])[0].get("w", "")
                    self.buffer += recognized_text  # 拼接识别到的文本
                    print(f"Partial recognition: {self.buffer}")
                    if "床前明月光" in self.buffer:  # 修改为您的唤醒词
                        print("Wake word detected!")
                        self.wake_word_detected = True
                        self.is_recording = False  # 停止录音
                        return
        except Exception as e:
            print(f"Error processing data: {e}")

    def close(self):
        """关闭 WebSocket 连接"""
        self.is_recording = False
        self.ws.close()
        print("Connection closed.")

if __name__ == "__main__":
    logging.basicConfig()
    client = Client()
    try:
        client.send_audio_stream()
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        client.close()

    if client.wake_word_detected:
        print("Wake word '床前明月光' detected. Exiting.")
