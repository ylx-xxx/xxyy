from flask import Flask, request, jsonify
import anthropic
import json
import os

app = Flask(__name__)

# ── 允许跨域（前后端分离时需要）──────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


# ── 健康检测 ───────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "BarbieChat API is running 💕"})


# ── 预检请求处理 ───────────────────────────────────────────────────────────
@app.route("/analyze", methods=["OPTIONS"])
def options():
    return jsonify({}), 200


# ── 核心分析接口 ───────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(silent=True) or {}
        chat_text = data.get("text", "").strip()

        if not chat_text:
            return jsonify({"error": "聊天记录不能为空哦~"}), 400

        if len(chat_text) > 20000:
            return jsonify({"error": "聊天记录太长啦，请控制在20000字以内~"}), 400

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return jsonify({"error": "API Key 未配置，请联系管理员~"}), 500

        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""你是一个温柔体贴的聊天记录分析助手，请分析以下聊天记录，提取关键信息。

聊天记录如下：
---
{chat_text}
---

请严格按照以下 JSON 格式返回分析结果，不要包含任何 Markdown 代码块标记或额外文字：
{{
  "sentiment": {{
    "overall": "正面 或 负面 或 中性",
    "score": 整数0到10,
    "description": "一句话描述整体情感氛围",
    "emotions": ["情绪标签1", "情绪标签2"]
  }},
  "events": [
    {{
      "date": "提到的日期或时间，没有则填空字符串",
      "content": "事件简要描述",
      "type": "社交 或 学习 或 工作 或 家庭 或 情感 或 其他"
    }}
  ],
  "relationships": [
    {{
      "name": "人物名称或称谓",
      "relation": "与对话者的关系描述"
    }}
  ],
  "summary": "整体摘要，100字以内，语气温柔活泼",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "advice": "给用户的一句贴心小建议"
}}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = message.content[0].text.strip()

        # 清理可能混入的 markdown 代码块
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip().rstrip("```").strip()

        result = json.loads(raw_text)
        return jsonify({"success": True, "data": result})

    except json.JSONDecodeError:
        return jsonify({"error": "AI 返回格式解析失败，请重试~"}), 500
    except anthropic.APIError as e:
        return jsonify({"error": f"AI 服务暂时不可用：{str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"服务器内部错误：{str(e)}"}), 500


# ── 每日摘要列表（示例接口，可接入数据库扩展）────────────────────────────
@app.route("/summaries", methods=["GET"])
def summaries():
    # TODO: 从数据库读取历史摘要
    return jsonify({"success": True, "data": [], "message": "暂无历史摘要~"})


# ── 本地开发时直接运行 ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)