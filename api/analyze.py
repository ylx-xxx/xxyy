import json
import os
import requests
from http.server import BaseHTTPRequestHandler

# ================= 配置区 =================
# 把你申请的百度云 API Key 和 Secret Key 填在这里！！！
API_KEY = "xOYlAVmGXZNv5nWf8LZXPSiD"
SECRET_KEY = "6N3d9y4ifjmdUBWTN5aiBJEYGqiCuXVA"

# 数据库文件路径（Vercel允许在 /tmp 目录下临时读写，但注意：函数冷启动时会被清空）
DB_FILE = "/tmp/chat_history.json"

# ================= 数据库操作区 =================
def read_db():
    """读取本地JSON数据库"""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_db(data):
    """写入本地JSON数据库"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================= 百度API调用区 =================
def get_baidu_token():
    """获取百度云的Access Token"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={API_KEY}&client_secret={SECRET_KEY}"
    response = requests.get(url)
    return response.json().get("access_token")

def analyze_sentiment(text):
    """调用百度情感倾向分析API"""
    token = get_baidu_token()
    if not token:
        return {"error": "获取百度API Token失败，请检查API_KEY"}
    
    url = f"https://aip.baidubce.com/rpc/2.0/nlp/v1/sentiment_classify?charset=UTF-8&access_token={token}"
    
    # 百度API限制单次调用文本长度，这里做简单切片（实际生产需更复杂的分片逻辑）
    max_len = 2048
    text_to_analyze = text[:max_len] if len(text) > max_len else text
    
    payload = json.dumps({"text": text_to_analyze})
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(url, headers=headers, data=payload.encode("utf-8"))
        result = response.json()
        
        if "items" in result:
            # 取第一段文本的分析结果
            item = result["items"][0]
            sentiment_prob = item.get("sentiment", 2) # 0负面, 1中性, 2正面
            confidence = item.get("confidence", 0)
            
            # 映射为芭比风格文案
            if sentiment_prob == 2:
                mood = "开心甜蜜"
            elif sentiment_prob == 0:
                mood = "有点小情绪"
            else:
                mood = "平平淡淡"
            return {"mood": mood, "confidence": confidence}
        else:
            return {"error": result.get("error_msg", "分析失败")}
    except Exception as e:
        return {"error": str(e)}

# ================= Vercel 路由处理区 =================
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """处理分析请求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request_body = json.loads(post_data)
        
        text = request_body.get("text", "")
        if not text:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "聊天记录不能为空哦~"}).encode("utf-8"))
            return

        # 1. 调用AI分析
        ai_result = analyze_sentiment(text)
        
        # 2. 准备存入数据库的记录
        record = {
            "id": len(read_db()) + 1,
            "date": request_body.get("date", "未知日期"),
            "preview": text[:50] + "..." if len(text) > 50 else text,
            "result": ai_result
        }
        
        # 3. 写入数据库
        db_data = read_db()
        db_data.append(record)
        write_db(db_data)
        
        # 4. 返回给前端
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"message": "AI帮你分析好啦！", "data": record}).encode("utf-8"))

    def do_GET(self):
        """获取历史分析记录（读取数据库）"""
        db_data = read_db()
        # 按照文档要求，返回时可以考虑脱敏，这里简单反转显示
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"history": db_data}).encode("utf-8"))
