# 📊 小渔奖惩打分系统

给孩子用的成长积分管理系统。用打分的方式激励好习惯、管理行为。

## 功能

- ⭐ 自定义打分规则（加分/减分）
- 📝 每次打分记录理由
- 📈 每日/周/月趋势图表
- 🏆 累计积分与目标奖励
- 🥇 规则排行榜
- 📐 数学错题本（含）

## 快速启动

```bash
pip install -r requirements.txt
python run.py
```

访问 http://localhost:5000/xiaoyu/scoring

## 技术栈

- Python 3 + Flask
- SQLite（本地数据库，零配置）
- Chart.js（前端图表）
- Bootstrap 5（UI框架）
