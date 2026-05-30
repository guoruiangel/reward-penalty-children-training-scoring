"""
小渔奖惩打分系统 - Flask Blueprint 路由模块
"""

from flask import Blueprint, render_template, request, jsonify
import sqlite3
from datetime import datetime
import os

xiaoyu = Blueprint('xiaoyu', __name__, url_prefix='/xiaoyu')

# ── 数据库路径 ──
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scores.db')


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables():
    """确保所需数据库表存在（自动建表）"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS xiaoyu_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score REAL NOT NULL DEFAULT 1.0,
            category TEXT DEFAULT '未分类',
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS xiaoyu_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER,
            score REAL NOT NULL,
            reason TEXT,
            period TEXT DEFAULT '',
            period_category TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS xiaoyu_math_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT '未分类',
            difficulty INTEGER DEFAULT 2,
            mastered INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mastered_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS xiaoyu_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_score REAL NOT NULL DEFAULT 100,
            reward TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ── 页面路由 ──

@xiaoyu.route('/')
def index():
    return render_template('index.html')

@xiaoyu.route('/scoring')
def scoring():
    return render_template('scoring.html')


# ── 打分规则 API ──

@xiaoyu.route('/api/rules', methods=['GET'])
def list_rules():
    ensure_tables()
    conn = get_db()
    rows = conn.execute('SELECT * FROM xiaoyu_rules ORDER BY score DESC').fetchall()
    conn.close()
    return jsonify({'rules': [dict(r) for r in rows]})


@xiaoyu.route('/api/rules', methods=['POST'])
def add_rule():
    data = request.get_json()
    name = data.get('name', '').strip()
    score = data.get('score', 1)
    category = data.get('category', '未分类')
    if not name:
        return jsonify({'success': False, 'error': '名称不能为空'}), 400
    ensure_tables()
    conn = get_db()
    conn.execute('INSERT INTO xiaoyu_rules (name, score, category) VALUES (?, ?, ?)',
                 (name, score, category))
    conn.commit()
    rule_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    return jsonify({'success': True, 'id': rule_id})


@xiaoyu.route('/api/rules/<int:rule_id>', methods=['PUT'])
def update_rule(rule_id):
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '无数据'}), 400
    ensure_tables()
    conn = get_db()
    updates = []
    params = []
    for field in ['name', 'score', 'category', 'enabled']:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])
    if not updates:
        conn.close()
        return jsonify({'success': False, 'error': '没有需要更新的字段'}), 400
    params.append(rule_id)
    conn.execute(f'UPDATE xiaoyu_rules SET {", ".join(updates)} WHERE id = ?', params)
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@xiaoyu.route('/api/rules/<int:rule_id>', methods=['DELETE'])
def delete_rule(rule_id):
    ensure_tables()
    conn = get_db()
    conn.execute('DELETE FROM xiaoyu_rules WHERE id = ?', (rule_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# ── 打分记录 API ──

@xiaoyu.route('/api/scores', methods=['GET'])
def list_scores():
    ensure_tables()
    conn = get_db()
    rows = conn.execute('''
        SELECT s.*, r.name as rule_name
        FROM xiaoyu_scores s
        LEFT JOIN xiaoyu_rules r ON s.rule_id = r.id
        ORDER BY s.created_at DESC
        LIMIT 50
    ''').fetchall()
    conn.close()
    return jsonify({'scores': [dict(r) for r in rows]})


@xiaoyu.route('/api/scores', methods=['POST'])
def add_score():
    data = request.get_json()
    rule_id = data.get('rule_id')
    reason = data.get('reason', '')
    period = data.get('period', '')
    period_category = data.get('period_category', '')
    ensure_tables()
    conn = get_db()
    rule = conn.execute('SELECT score, category FROM xiaoyu_rules WHERE id = ?', (rule_id,)).fetchone()
    if not rule:
        conn.close()
        return jsonify({'success': False, 'error': '规则不存在'}), 404
    if not period_category:
        period_category = rule['category'] or ''
    conn.execute('INSERT INTO xiaoyu_scores (rule_id, score, reason, period, period_category) VALUES (?, ?, ?, ?, ?)',
                 (rule_id, rule['score'], reason, period, period_category))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@xiaoyu.route('/api/scores/<int:score_id>', methods=['DELETE'])
def delete_score(score_id):
    ensure_tables()
    conn = get_db()
    cur = conn.execute('DELETE FROM xiaoyu_scores WHERE id = ?', (score_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        return jsonify({'success': False, 'error': '记录不存在'}), 404
    return jsonify({'success': True})


@xiaoyu.route('/api/scores/<int:score_id>', methods=['PUT'])
def update_score(score_id):
    data = request.get_json()
    reason = data.get('reason')
    rule_id = data.get('rule_id')
    ensure_tables()
    conn = get_db()
    if reason is not None:
        conn.execute('UPDATE xiaoyu_scores SET reason = ? WHERE id = ?', (reason, score_id))
    if rule_id is not None:
        rule = conn.execute('SELECT score FROM xiaoyu_rules WHERE id = ?', (rule_id,)).fetchone()
        if not rule:
            conn.close()
            return jsonify({'success': False, 'error': '规则不存在'}), 404
        conn.execute('UPDATE xiaoyu_scores SET rule_id = ?, score = ? WHERE id = ?',
                     (rule_id, rule['score'], score_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@xiaoyu.route('/api/scores/stats', methods=['GET'])
def score_stats():
    ensure_tables()
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    today_dt = datetime.now()
    week_start = (today_dt - __import__('datetime').timedelta(days=today_dt.weekday())).strftime('%Y-%m-%d')
    month = datetime.now().strftime('%Y-%m')

    today_total = conn.execute(
        "SELECT COALESCE(SUM(score), 0) FROM xiaoyu_scores WHERE created_at >= ?",
        (today,)
    ).fetchone()[0]

    week_total = conn.execute(
        "SELECT COALESCE(SUM(score), 0) FROM xiaoyu_scores WHERE created_at >= ?",
        (week_start,)
    ).fetchone()[0]

    month_total = conn.execute(
        "SELECT COALESCE(SUM(score), 0) FROM xiaoyu_scores WHERE created_at LIKE ?",
        (f'{month}%',)
    ).fetchone()[0]

    all_total = conn.execute(
        "SELECT COALESCE(SUM(score), 0) FROM xiaoyu_scores"
    ).fetchone()[0]

    rule_counts = conn.execute('''
        SELECT r.name, COUNT(*) as cnt, SUM(s.score) as total
        FROM xiaoyu_scores s
        JOIN xiaoyu_rules r ON s.rule_id = r.id
        GROUP BY s.rule_id
        ORDER BY total DESC
        LIMIT 10
    ''').fetchall()

    conn.close()
    return jsonify({
        'today_total': today_total,
        'week_total': week_total,
        'month_total': month_total,
        'all_total': all_total,
        'top_rules': [dict(r) for r in rule_counts]
    })


# ── 目标奖励 API ──

@xiaoyu.route('/api/goals', methods=['GET', 'POST'])
def goals_api():
    ensure_tables()
    conn = get_db()

    if request.method == 'GET':
        goal = conn.execute('SELECT * FROM xiaoyu_goals ORDER BY id DESC LIMIT 1').fetchone()
        conn.close()
        if goal:
            return jsonify({'success': True, 'goal': dict(goal)})
        return jsonify({'success': True, 'goal': None})

    data = request.get_json()
    target_score = data.get('target_score', 100)
    reward = data.get('reward', '')
    cursor = conn.execute('INSERT INTO xiaoyu_goals (target_score, reward) VALUES (?, ?)',
                 (target_score, reward))
    conn.commit()
    goal_id = cursor.lastrowid
    goal = conn.execute('SELECT * FROM xiaoyu_goals WHERE id = ?', (goal_id,)).fetchone()
    conn.close()
    return jsonify({'success': True, 'goal': dict(goal)})
