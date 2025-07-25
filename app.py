from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import json
import os
import datetime

app = Flask(__name__)

# --- 数据库配置 ---
# 1. 从环境变量获取数据库URL。这是为了部署到Render/Zéabur等平台。
# 2. 如果环境变量里没有，就使用本地的SQLite数据库文件，方便本地测试。
db_url = os.environ.get("DATABASE_URL", "sqlite:///chat_history.db")
# 替换postgresql:// 为 postgresqpsycopg2:// 如果需要（某些平台的旧格式）
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- 数据库模型定义 ---
# 我们定义一个 Message 表来存储聊天记录
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(15), nullable=False)  # 'user' or 'ai'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {"role": self.role, "content": self.content}


# --- API配置 ---
AI_API_URL = "https://api.st0722.top/v1/chat/completions"
AI_API_KEY = os.environ.get("AI_API_KEY", "sk-IoYmXE15HCpj9tAnm3T4IDnNINb3joYwS63LjWX1XmZV0Spc")


# --- 路由和视图函数 ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    # 这部分逻辑和之前类似，但增加了保存消息到数据库的步骤
    try:
        data = request.get_json()
        user_message_content = data.get('message')
        selected_model = data.get('model', 'gpt-4.1')

        if not user_message_content:
            return jsonify({"error": "Message is empty"}), 400

        # --- 1. 调用AI ---
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {AI_API_KEY}'}
        payload = {"model": selected_model, "messages": [{"role": "user", "content": user_message_content}], "stream": False}
        response = requests.post(AI_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        ai_message_content = response.json()['choices'][0]['message']['content']

        # --- 2. 将用户消息和AI回复都存入数据库 ---
        user_msg = Message(role='user', content=user_message_content)
        ai_msg = Message(role='ai', content=ai_message_content)
        db.session.add(user_msg)
        db.session.add(ai_msg)
        db.session.commit()

        # --- 3. 返回AI的回复给前端 ---
        return jsonify({"reply": ai_message_content})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"无法连接到AI服务: {e}"}), 500
    except Exception as e:
        db.session.rollback() # 如果保存出错，回滚数据库操作
        print(f"An error occurred: {e}")
        return jsonify({"error": "服务器内部错误"}), 500


# --- 新增API：获取历史记录 ---
@app.route('/history', methods=['GET'])
def get_history():
    messages = Message.query.order_by(Message.timestamp.asc()).all()
    return jsonify([msg.to_dict() for msg in messages])


# --- 新增API：清空历史记录 ---
@app.route('/clear', methods=['POST'])
def clear_history():
    try:
        db.session.query(Message).delete()
        db.session.commit()
        return jsonify({"success": "聊天记录已清空"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"清空失败: {e}"}), 500


# --- 初始化数据库 ---
# 这段代码确保在第一次运行app时，如果数据库和表不存在，就会自动创建它们。
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)