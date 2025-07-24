from flask import Flask, render_template, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# --- 在这里配置你的AI API信息 ---
AI_API_URL = "https://api.st0722.top/v1/chat/completions"
AI_API_KEY = os.environ.get("AI_API_KEY", "sk-IoYmXE15HCpj9tAnm3T4IDnNiNB3joYwS63LjWX1XmZV0Spc")   # 这里是你自己的Key


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get('message')
        print(f"--- 收到来自前端的消息: {user_message} ---")
        if not user_message:
            print("错误：收到的消息为空。")
            return jsonify({"error": "Message is empty"}), 400
    except Exception as e:
        print(f"错误：解析前端请求失败: {e}")
        return jsonify({"error": f"Invalid request from frontend: {e}"}), 400

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {AI_API_KEY}'
    }
    payload = {
        "model": "gpt-4.1",
        "messages": [{"role": "user", "content": user_message}],
        "stream": False  # 重要补充！
    }
    print(f"--- 准备发送到AI API的Payload: {json.dumps(payload, indent=2)} ---")

    try:
        print("--- 正在发送请求到AI API... ---")
        response = requests.post(AI_API_URL, headers=headers, data=json.dumps(payload), timeout=30)

        print(f"--- AI API响应状态码: {response.status_code} ---")
        print(f"--- AI API原始响应内容: {response.text} ---")

        response.raise_for_status()

        ai_response_data = response.json()
        ai_message = ai_response_data['choices'][0]['message']['content']
        print(f"--- 成功解析AI回复: {ai_message} ---")

        return jsonify({"reply": ai_message})

    except requests.exceptions.RequestException as e:
        print(f"致命错误：API请求失败: {e}")
        return jsonify({"error": f"无法连接到AI服务: {e}"}), 500
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"致命错误：解析AI响应失败: {e}")
        return jsonify({"error": "无法解析AI的回复，请检查PyCharm终端日志查看API返回的原始信息。"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)