import os
import sqlite3
from dashscope import MultiModalConversation
from datetime import datetime
import uuid
from uuid import uuid4
import tempfile
from picture_mod import take_picture
from tablestore import OTSClient, Row, Condition, INF_MIN, INF_MAX
# from text_to_speech import speak

class SQLiteDB:
    """SQLite implementation for storing query history."""
    def __init__(self, db_name="database.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_table()

    def create_table(self):
        """Create the queries table if it doesn't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id TEXT PRIMARY KEY,
                file_id TEXT,
                image_url TEXT,
                created_at TIMESTAMP,
                input_prompt TEXT,
                output_response TEXT
            )
        """)
        self.connection.commit()

    def save_data(self, data):
        """Save query data to the database."""
        self.cursor.execute("""
            INSERT INTO queries (id, file_id, image_url, created_at, input_prompt, output_response)
            VALUES (:id, :file_id, :image_url, :created_at, :input_prompt, :output_response)
        """, data)
        self.connection.commit()

    def get_data(self, limit=100):
        """Retrieve the most recent query history."""
        self.cursor.execute("""
            SELECT file_id, image_url, created_at, input_prompt, output_response 
            FROM queries 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()


db = SQLiteDB()

def create_history_from_sqlite(n: int = 100):
    """Create history object for Aliyun model from SQLite data."""
    n = min(n, 1000)
    items = db.get_data(limit=n)
    messages = []

    for item in items:
        file_id, image_url, created_at, input_prompt, output_response = item
        
        # Add user's message
        user_message = {
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": input_prompt}
            ]
        }
        messages.append(user_message)

        # Add model's response as Assistant message
        assistant_message = {
            "role": "assistant",
            "content": [
                {"text": output_response}
            ]
        }
        messages.append(assistant_message)

    return messages


initial_history = create_history_from_sqlite(10)

from obs import ObsClient

# 配置 OBS 客户端
ACCESS_OBS_KEY = os.getenv('ACCESS_OBS_KEY')  # 从环境变量获取 Access Key
SECRET_OBS_KEY = os.getenv('SECRET_OBS_KEY')  # 从环境变量获取 Secret Key
OBS_ENDPOINT = os.getenv('OBS_ENDPOINT', 'https://obs.cn-south-1.myhuaweicloud.com')  # 获取 Endpoint，提供默认值
OBS_BUCKET_NAME = os.getenv('OBS_BUCKET_NAME', 'insight')  # 获取 Bucket 名称，提供默认值
OBS_ENDPOINT_NO_HTTP = os.getenv('OBS_ENDPOINT_NO_HTTP', 'obs.cn-south-1.myhuaweicloud.com')

# 初始化 OBS 客户端
obs_client = ObsClient(
    access_key_id=ACCESS_OBS_KEY,
    secret_access_key=SECRET_OBS_KEY,
    server=OBS_ENDPOINT
)

def upload_file_to_storage(filepath: str, object_name: str) -> str:
    """
    上传文件到华为云 OBS 并返回文件的访问 URL。

    :param filepath: 本地文件路径
    :param object_name: 上传到 OBS 的对象名称
    :return: 文件的访问 URL
    """
    try:
        # 上传文件到指定桶
        response = obs_client.putFile(bucketName=OBS_BUCKET_NAME, objectKey=object_name, file_path=filepath)
        
        if response.status < 300:
            # 生成文件访问 URL
            file_url = f"https://{OBS_BUCKET_NAME}.{OBS_ENDPOINT_NO_HTTP}/{object_name}"
            print(f"File uploaded successfully: {file_url}")
            return file_url
        else:
            print(f"Failed to upload file. Status: {response.status}, Error: {response.errorMessage}")
            raise Exception(f"OBS Upload failed: {response.errorMessage}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

ALI_VL_KEY = os.getenv('ALI_VL_KEY')  # 从环境变量获取 Aliyun API Key

def get_response(prompt: str) -> str:
    """答复用户问题，并上传图片至表格存储"""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        # filepath = temp_file.name
        # take_picture(filepath)  # 拍摄图片 code in picture.py
        # print(f"Captured image saved to {filepath}")

        # 上传图片到云存储并获取其 URL
        # image_url = upload_file_to_storage(filepath)
        # print(f"Uploaded image URL: {image_url}")
        image_url = 'https://insight.obs.cn-south-1.myhuaweicloud.com/test1.png'

        # 生成消息内容
        messages = initial_history  # Fetch last 10 messages from SQLite
        # Add new user message
        user_message = {
            "role": "user",
            "content": [
                {"image": image_url},
                {"text": prompt}
            ]
        }
        messages.append(user_message)
        print("请求的message：", messages)

        # 调用阿里云 qwen-plus 模型
        try:
            print("Sending request to Llama model...")
            # speak("正在分析图片并回答问题，请稍候。")
            response = MultiModalConversation.call(
                api_key=ALI_VL_KEY,  # 使用环境变量获取 API Key
                model="qwen-vl-plus",
                messages=messages,
            )
        except Exception as e:
            print(f"Error while calling Llama model: {e}")
            return "对不起，处理请求时发生了错误。"

        # 解析响应
        if response.status_code == 200:
            response_text = response.output.choices[0].message.content[0]["text"]
            print(f"Model response: {response_text}")

            # Save query record to SQLite
            data = {
                "id": uuid4().hex,
                "file_id": uuid.uuid4().hex,
                "image_url": image_url,
                "created_at": datetime.now(),
                "input_prompt": prompt,
                "output_response": response_text
            }
            db.save_data(data)
        else:
            error_message = (
                f"Request failed: Status code {response.status_code}, "
                f"Error code: {response.code}, Message: {response.message}"
            )
            print(error_message)
            response_text = "对不起，无法生成答案。"

    # 删除临时文件
    # os.unlink(filepath)
    return response_text


if __name__ == "__main__":
    print('initial history:', initial_history)
    # while True:
    # user_input = input("Enter your question: ")
    response = get_response('请描述图片中的内容')
    print(response)
    print("\n")

    # filepath = '3ac4-hvvuiyp2168162.jpg'
    # # 上传图片到云存储并获取其 URL
    # image_url = upload_file_to_storage(filepath, 'test2.jpg')
    # # https://insight.obs.cn-south-1.myhuaweicloud.com/test2.jpg
    # print(f"Uploaded image URL: {image_url}")
