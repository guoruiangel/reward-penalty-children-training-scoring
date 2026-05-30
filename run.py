#!/usr/bin/env python3
"""
小渔奖惩打分系统 - 启动入口
运行: python run.py
"""

from flask import Flask
from app import xiaoyu
import os

app = Flask(__name__)
app.secret_key = 'xiaoyu-scoring-secret-key'
app.register_blueprint(xiaoyu)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 小渔奖惩打分系统启动: http://0.0.0.0:{port}/xiaoyu/scoring")
    app.run(host='0.0.0.0', port=port, debug=True)
