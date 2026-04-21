import json
import os
from aip import AipNlp

# ================= 配置区 ================= #
API_KEY = os.environ.get("BAIDU_API_KEY", "")
SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
CLIENT = AipNlp(API_KEY, SECRET_KEY) if API_KEY and SECRET_KEY else None  # 初始化百度 NLP 客户端

# 数据库文件路径（Vercel 允许 /tmp 临时读写，冷启动会清空）
DB_FILE = "/tmp/chat_history.json"

# ================= 数据库操作区 ================= #
def read_db():
    """读取本地 JSON 数据库"""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_db(data):
    """写入本地 JSON 数据库"""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================= 百度 API 调用区 ================= #
def analyze_sentiment(text):
    """调用百度情感倾向分析 API（使用 SDK 封装方法）"""
    if not CLIENT:
        return {"error": "百度 API Key 或 Secret Key 未配置，请在 Vercel 环境变量中设置"}
    try:
        # 使用 AipNlp 的 sentimentClassify 方法（自动处理 Token）
        result = CLIENT.sentimentClassify(text)
        if "items" in result:
            item = result["items"][0]
            sentiment_prob = item.get("sentiment", 2)  # 0:负面, 1:中性, 2:正面
            confidence = item.get("confidence", 0)
            # 映射为芭比风格文案
            mood = "开心甜蜜" if sentiment_prob == 2 else "有点小情绪" if sentiment_prob == 0 else "平平淡淡"
            return {"mood": mood, "confidence": confidence}
        else:
            return {"error": result.get("error_msg", "分析失败")}
    except Exception as e:
        return {"error": f"分析过程中出错: {str(e)}"}

# ================= Vercel 路由处理区 ================= #
def handler(event, context):
    """Vercel Serverless 函数入口，根据 HTTP 方法处理请求"""
    import json
    http_method = event['httpMethod']
    
    if http_method == 'POST':
        # 处理 POST 请求（分析聊天记录）
        post_data = event['body']
        try:
            request_body = json.loads(post_data)
        except json.JSONDecodeError:
            return {'statusCode': 400, 'body': json.dumps({"error": "请求体格式错误，请检查 JSON 格式"})}
        
        text = request_body.get("text", "")
        date = request_body.get("date", "未知日期")
        if not text:
            return {'statusCode': 400, 'body': json.dumps({"error": "聊天记录不能为空哦~"})}
        
        # 调用 AI 分析
        ai_result = analyze_sentiment(text)
        if "error" in ai_result:
            return {'statusCode': 500, 'body': json.dumps({"error": ai_result["error"]})}
        
        # 准备存入数据库的记录
        record = {
            "id": len(read_db()) + 1,
            "date": date,
            "preview": text[:50] + "..." if len(text) > 50 else text,
            "result": ai_result
        }
        
        # 写入数据库
        db_data = read_db()
        db_data.append(record)
        write_db(db_data)
        
        # 返回成功结果
        return {
            'statusCode': 200,
            'body': json.dumps({"message": "AI帮你分析好啦！", "data": record})
        }
    
    elif http_method == 'GET':
        # 处理 GET 请求（获取历史记录）
        db_data = read_db()
        return {'statusCode': 200, 'body': json.dumps({"history": db_data})}
    
    else:
        # 不支持的 HTTP 方法
        return {'statusCode': 405, 'body': json.dumps({"error": "不支持的 HTTP 方法"})}
