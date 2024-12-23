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

class Client():
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
        self.wake_word_detected = False  # 用于保存唤醒词检测状态
        self.buffer = ""  # 用于拼接识别结果的缓冲区
        self.trecv.start()

    def send(self, file_path):
        file_object = open(file_path, 'rb')
        try:
            while True:
                if self.wake_word_detected:
                    return
                chunk = file_object.read(1280)
                if not chunk:
                    break
                self.ws.send(chunk)
                time.sleep(0.04)
        finally:
            file_object.close()

        self.ws.send(bytes(self.end_tag.encode('utf-8')))
        print("send end tag success")

    def recv(self):
        try:
            while self.ws.connected:
                result = str(self.ws.recv())
                if len(result) == 0:
                    print("receive result end")
                    break
                result_dict = json.loads(result)
                if result_dict["action"] == "started":
                    print("handshake success, result: " + result)
                if result_dict["action"] == "result":
                    # 检查是否检测到唤醒词
                    if self.detect_wake_word(result_dict["data"]) == True:
                        return True
                if result_dict["action"] == "error":
                    print("rtasr error: " + result)
                    self.ws.close()
                    return
        except websocket.WebSocketConnectionClosedException:
            print("receive result end")

    def detect_wake_word(self, data):
        """解析返回的数据并检测是否包含唤醒词"""
        try:
            result_data = json.loads(data)
            words = result_data.get("cn", {}).get("st", {}).get("rt", [])
            for segment in words:
                for word in segment.get("ws", []):
                    recognized_text = word.get("cw", [{}])[0].get("w", "")
                    self.buffer += recognized_text  # 将识别到的文本拼接到缓冲区
                    print(self.buffer)
                    if "床前明月光" in self.buffer:
                        print("唤醒词检测到: 你好")
                        self.wake_word_detected = True
                        return True
        except Exception as e:
            print(f"解析数据时出错: {e}")
        return False

    def close(self):
        self.ws.close()
        print("connection closed")

if __name__ == '__main__':
    logging.basicConfig()

    app_id = os.getenv('XUNFEI_APP_ID')
    api_key = os.getenv('XUNFEI_API_KEY')
    # 先以音频文件为例
    file_path = r"./test_1.pcm"

    client = Client()
    client.send(file_path)

    # 检测唤醒词
    while not client.wake_word_detected:
        time.sleep(0.1)

    print("唤醒词 '你好' 已检测到，返回 True")
    client.close()

# handshake success, result: {"action":"started","code":"0","data":"","desc":"success","sid":"rta0d2ff81d@dx2f5f1ac4128b000100"}
# 床
# 床前
# 床前床
# 床前床前
# 床前床前明
# 床前床前明月光
# 唤醒词检测到: 你好
# 唤醒词 '你好' 已检测到，返回 True
# connection closed

