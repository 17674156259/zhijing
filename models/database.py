"""
数据库模块
=========
使用 SQLite 存储用户、诊断记录和练习记录。

表结构：
- users: 用户账号
- diagnoses: 每次错题诊断的完整记录
- practice_records: 每次练习的记录
- chat_messages: AI 追问对话记录
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from config import Config
from utils.logger import logger

LOCAL_TZ = timezone(timedelta(hours=8))


def _local_now():
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT,
            role TEXT DEFAULT 'student',
            class_code TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            teacher_id INTEGER NOT NULL,
            created_at TEXT,
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT DEFAULT '高等数学',
            question TEXT NOT NULL,
            student_answer TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            image_path TEXT,
            result_json TEXT NOT NULL,
            knowledge_point TEXT,
            mastery_estimate REAL,
            weakness TEXT,
            is_favorite INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS practice_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            diagnosis_id INTEGER,
            weakness TEXT,
            accuracy INTEGER,
            total_questions INTEGER,
            correct_count INTEGER,
            created_at TEXT,
            FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diagnosis_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id)
        );

        CREATE TABLE IF NOT EXISTS question_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            knowledge_point TEXT NOT NULL,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            correct INTEGER NOT NULL,
            explanation TEXT DEFAULT '',
            is_preset INTEGER DEFAULT 0,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS knowledge_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            knowledge_point TEXT NOT NULL,
            subject TEXT NOT NULL,
            p_learn REAL DEFAULT 0.3,
            practice_count INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            updated_at TEXT,
            UNIQUE(user_id, knowledge_point, subject)
        );
    """)

    # 迁移：如果旧表缺少新列则添加
    try:
        db.execute("SELECT subject FROM diagnoses LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE diagnoses ADD COLUMN subject TEXT DEFAULT '高等数学'")
    try:
        db.execute("SELECT image_path FROM diagnoses LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE diagnoses ADD COLUMN image_path TEXT")
    try:
        db.execute("SELECT role FROM users LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
    try:
        db.execute("SELECT class_code FROM users LIMIT 1")
    except sqlite3.OperationalError:
        db.execute("ALTER TABLE users ADD COLUMN class_code TEXT")

    db.commit()
    db.close()
    logger.info("数据库初始化完成")


# ============================================================
#  用户 CRUD
# ============================================================

def create_user(username, password_hash, nickname=None, role='student', class_code=None):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO users (username, password_hash, nickname, role, class_code, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, password_hash, nickname or username, role, class_code, _local_now())
    )
    db.commit()
    user_id = cursor.lastrowid
    db.close()
    logger.info(f"新用户注册: id={user_id}, username={username}, role={role}")
    return user_id


def get_user_by_username(username):
    db = get_db()
    row = db.execute(
        """SELECT u.*, c.name as class_name
           FROM users u LEFT JOIN classes c ON c.code = u.class_code
           WHERE u.username = ?""",
        (username,)
    ).fetchone()
    db.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    db = get_db()
    row = db.execute(
        """SELECT u.id, u.username, u.nickname, u.role, u.class_code, u.created_at,
                  c.name as class_name
           FROM users u LEFT JOIN classes c ON c.code = u.class_code
           WHERE u.id = ?""",
        (user_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else None


# ============================================================
#  诊断记录 CRUD
# ============================================================

def save_diagnosis(question, student_answer, correct_answer, result, user_id=None, subject="高等数学", image_path=None):
    db = get_db()
    cursor = db.execute(
        """INSERT INTO diagnoses
           (user_id, subject, question, student_answer, correct_answer, image_path,
            result_json, knowledge_point, mastery_estimate, weakness, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            subject,
            question,
            student_answer,
            correct_answer,
            image_path,
            json.dumps(result, ensure_ascii=False),
            result.get("primary_knowledge_point", {}).get("name", ""),
            result.get("mastery_estimate", 0),
            result.get("weakness", ""),
            _local_now()
        )
    )
    db.commit()
    record_id = cursor.lastrowid
    db.close()
    logger.info(f"诊断记录已保存: id={record_id}, user_id={user_id}")
    return record_id


def get_diagnosis_by_id(record_id):
    db = get_db()
    row = db.execute("SELECT * FROM diagnoses WHERE id = ?", (record_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_diagnosis_list(limit=20, user_id=None, favorite_only=False):
    db = get_db()
    sql = """SELECT id, subject, question, student_answer, correct_answer, result_json,
                    knowledge_point, mastery_estimate, weakness,
                    is_favorite, notes, image_path, created_at
             FROM diagnoses WHERE 1=1"""
    params = []

    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    else:
        sql += " AND user_id IS NULL"

    if favorite_only:
        sql += " AND is_favorite = 1"

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(row) for row in rows]


def update_diagnosis_favorite(record_id, is_favorite):
    db = get_db()
    db.execute("UPDATE diagnoses SET is_favorite = ? WHERE id = ?", (1 if is_favorite else 0, record_id))
    db.commit()
    db.close()


def update_diagnosis_notes(record_id, notes):
    db = get_db()
    db.execute("UPDATE diagnoses SET notes = ? WHERE id = ?", (notes, record_id))
    db.commit()
    db.close()


def delete_diagnosis(record_id):
    db = get_db()
    db.execute("DELETE FROM practice_records WHERE diagnosis_id = ?", (record_id,))
    db.execute("DELETE FROM chat_messages WHERE diagnosis_id = ?", (record_id,))
    db.execute("DELETE FROM diagnoses WHERE id = ?", (record_id,))
    db.commit()
    db.close()


def get_knowledge_stats(user_id=None):
    """按知识点统计掌握度"""
    db = get_db()
    sql = """SELECT knowledge_point,
                    COUNT(*) as count,
                    AVG(mastery_estimate) as avg_mastery,
                    MAX(mastery_estimate) as max_mastery,
                    MIN(mastery_estimate) as min_mastery
             FROM diagnoses
             WHERE knowledge_point IS NOT NULL AND knowledge_point != ''"""
    params = []
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    else:
        sql += " AND user_id IS NULL"
    sql += " GROUP BY knowledge_point ORDER BY count DESC"

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(row) for row in rows]


# ============================================================
#  练习记录 CRUD
# ============================================================

def save_practice_record(diagnosis_id, weakness, accuracy, total, correct, user_id=None):
    db = get_db()
    cursor = db.execute(
        """INSERT INTO practice_records
           (user_id, diagnosis_id, weakness, accuracy, total_questions, correct_count, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, diagnosis_id, weakness, accuracy, total, correct, _local_now())
    )
    db.commit()
    record_id = cursor.lastrowid
    db.close()
    return record_id


def get_practice_stats(user_id=None):
    db = get_db()
    sql = """SELECT
               COUNT(*) as total_sessions,
               AVG(accuracy) as avg_accuracy,
               SUM(total_questions) as total_questions,
               SUM(correct_count) as total_correct
           FROM practice_records WHERE 1=1"""
    params = []
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    else:
        sql += " AND user_id IS NULL"

    row = db.execute(sql, params).fetchone()
    db.close()
    return dict(row) if row else {"total_sessions": 0, "avg_accuracy": 0, "total_questions": 0, "total_correct": 0}


def get_practice_trend(user_id=None, limit=10):
    """获取最近练习的正确率趋势"""
    db = get_db()
    sql = "SELECT accuracy, total_questions, correct_count, weakness, created_at FROM practice_records WHERE 1=1"
    params = []
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    else:
        sql += " AND user_id IS NULL"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(sql, params).fetchall()
    db.close()
    return [dict(row) for row in reversed(rows)]  # 反转让时间正序


# ============================================================
#  对话记录 CRUD（AI 追问）
# ============================================================

def save_chat_message(diagnosis_id, role, content):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO chat_messages (diagnosis_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (diagnosis_id, role, content, _local_now())
    )
    db.commit()
    msg_id = cursor.lastrowid
    db.close()
    return msg_id


def get_chat_history(diagnosis_id):
    db = get_db()
    rows = db.execute(
        "SELECT role, content, created_at FROM chat_messages WHERE diagnosis_id = ? ORDER BY id ASC",
        (diagnosis_id,)
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


# ============================================================
#  看板统计
# ============================================================

def get_dashboard_stats(user_id):
    """获取看板数据"""
    db = get_db()

    if user_id is not None:
        uid_filter = "AND user_id = ?"
        uid_params = (user_id,)
    else:
        uid_filter = "AND user_id IS NULL"
        uid_params = ()

    # 诊断统计
    diag_stats = db.execute(
        f"""SELECT
               COUNT(*) as total_diagnoses,
               AVG(mastery_estimate) as avg_mastery,
               COUNT(CASE WHEN is_favorite = 1 THEN 1 END) as favorites
           FROM diagnoses WHERE 1=1 {uid_filter}""",
        uid_params
    ).fetchone()

    # 练习统计
    practice_stats = db.execute(
        f"""SELECT
               COUNT(*) as total_sessions,
               AVG(accuracy) as avg_accuracy,
               SUM(total_questions) as total_questions,
               SUM(correct_count) as total_correct
           FROM practice_records WHERE 1=1 {uid_filter}""",
        uid_params
    ).fetchone()

    # 薄弱点分布
    weakness_stats = db.execute(
        f"""SELECT weakness, COUNT(*) as count
           FROM diagnoses WHERE 1=1 {uid_filter} AND weakness IS NOT NULL AND weakness != ''
           GROUP BY weakness ORDER BY count DESC LIMIT 10""",
        uid_params
    ).fetchall()

    # 掌握度趋势
    mastery_trend = db.execute(
        f"""SELECT mastery_estimate, knowledge_point, created_at
           FROM diagnoses WHERE 1=1 {uid_filter}
           ORDER BY created_at ASC LIMIT 20""",
        uid_params
    ).fetchall()

    # 知识点统计
    knowledge_stats = db.execute(
        f"""SELECT knowledge_point,
               COUNT(*) as count,
               AVG(mastery_estimate) as avg_mastery
           FROM diagnoses WHERE 1=1 {uid_filter}
             AND knowledge_point IS NOT NULL AND knowledge_point != ''
           GROUP BY knowledge_point ORDER BY count DESC""",
        uid_params
    ).fetchall()

    db.close()

    return {
        "diagnosis": dict(diag_stats) if diag_stats else {},
        "practice": dict(practice_stats) if practice_stats else {},
        "weakness_distribution": [dict(r) for r in weakness_stats],
        "mastery_trend": [dict(r) for r in mastery_trend],
        "knowledge_stats": [dict(r) for r in knowledge_stats],
    }


# ============================================================
#  班级管理
# ============================================================

import random as _random
import string as _string

def _gen_class_code():
    return ''.join(_random.choices(_string.ascii_uppercase + _string.digits, k=6))


def create_class(name, teacher_id):
    db = get_db()
    code = _gen_class_code()
    while db.execute("SELECT id FROM classes WHERE code = ?", (code,)).fetchone():
        code = _gen_class_code()
    cursor = db.execute(
        "INSERT INTO classes (code, name, teacher_id, created_at) VALUES (?, ?, ?, ?)",
        (code, name, teacher_id, _local_now())
    )
    db.commit()
    class_id = cursor.lastrowid
    db.close()
    logger.info(f"班级创建: id={class_id}, code={code}, teacher_id={teacher_id}")
    return {"id": class_id, "code": code, "name": name}


def get_class_by_code(code):
    db = get_db()
    row = db.execute("SELECT * FROM classes WHERE code = ?", (code,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_classes_by_teacher(teacher_id):
    db = get_db()
    rows = db.execute(
        """SELECT c.*, COUNT(u.id) as student_count
           FROM classes c LEFT JOIN users u ON u.class_code = c.code
           WHERE c.teacher_id = ?
           GROUP BY c.id ORDER BY c.created_at DESC""",
        (teacher_id,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_class_students(class_code):
    db = get_db()
    rows = db.execute(
        "SELECT id, username, nickname, created_at FROM users WHERE class_code = ? AND role = 'student' ORDER BY created_at",
        (class_code,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def update_user_class(user_id, class_code):
    db = get_db()
    db.execute("UPDATE users SET class_code = ? WHERE id = ?", (class_code, user_id))
    db.commit()
    db.close()


def get_class_dashboard(class_code):
    """获取班级整体看板数据"""
    db = get_db()
    student_ids = [r['id'] for r in db.execute(
        "SELECT id FROM users WHERE class_code = ? AND role = 'student'", (class_code,)
    ).fetchall()]

    if not student_ids:
        db.close()
        return {"total_students": 0, "total_diagnoses": 0, "weakness_distribution": [],
                "knowledge_distribution": [], "student_stats": []}

    placeholders = ','.join('?' * len(student_ids))

    total_diag = db.execute(
        f"SELECT COUNT(*) as cnt FROM diagnoses WHERE user_id IN ({placeholders})", student_ids
    ).fetchone()['cnt']

    # 薄弱点分布
    weakness_rows = db.execute(
        f"""SELECT weakness, COUNT(*) as count FROM diagnoses
            WHERE user_id IN ({placeholders}) AND weakness IS NOT NULL AND weakness != ''
            GROUP BY weakness ORDER BY count DESC LIMIT 10""",
        student_ids
    ).fetchall()

    # 知识点分布
    kp_rows = db.execute(
        f"""SELECT knowledge_point, COUNT(*) as count, AVG(mastery_estimate) as avg_mastery
            FROM diagnoses WHERE user_id IN ({placeholders})
            AND knowledge_point IS NOT NULL AND knowledge_point != ''
            GROUP BY knowledge_point ORDER BY count DESC""",
        student_ids
    ).fetchall()

    # 每个学生的统计
    student_stats = []
    for sid in student_ids:
        s = db.execute(
            """SELECT d.user_id, u.username, u.nickname,
                      COUNT(d.id) as diag_count,
                      AVG(d.mastery_estimate) as avg_mastery
               FROM diagnoses d JOIN users u ON u.id = d.user_id
               WHERE d.user_id = ? GROUP BY d.user_id""",
            (sid,)
        ).fetchone()
        if s:
            student_stats.append(dict(s))

    db.close()
    return {
        "total_students": len(student_ids),
        "total_diagnoses": total_diag,
        "weakness_distribution": [dict(r) for r in weakness_rows],
        "knowledge_distribution": [dict(r) for r in kp_rows],
        "student_stats": student_stats
    }


# ============================================================
#  知识点前置关系（同济版高等数学）
# ============================================================

KNOWLEDGE_GRAPH = {
    "nodes": [
        # 第一章
        {"id": "F01", "name": "函数的概念与性质", "chapter": "第一章 函数与极限", "difficulty": 1,
         "concept": "函数是集合间的一种映射关系，定义域和对应法则是函数的两要素。掌握奇偶性、单调性、有界性、周期性四大性质。",
         "common_exams": ["求函数定义域和值域", "判断函数奇偶性/周期性", "复合函数分解"],
         "common_errors": "忽略定义域限制（如分母不为零、根号内非负），混淆复合函数的分解顺序",
         "advice": "先把基本初等函数（幂、指、对、三角）的性质过一遍，再练复合函数分解。注意分段函数的定义域处理。",
         "keywords": ["定义域", "值域", "奇偶性", "单调性", "周期性", "反函数", "复合函数", "基本初等函数"]},
        {"id": "F02", "name": "极限的定义与计算", "chapter": "第一章 函数与极限", "difficulty": 2,
         "concept": "极限描述函数在趋近某点时的变化趋势。掌握ε-δ定义、极限四则运算法则、两个重要极限、夹逼准则和单调有界准则。",
         "common_exams": ["求各类极限（0/0型、∞/∞型）", "利用两个重要极限求值", "夹逼准则的应用"],
         "common_errors": "直接代入未验证连续性就使用极限四则运算，忽略未定式的处理步骤",
         "advice": "先掌握直接代入法，再学等价无穷小替换。两个重要极限 lim(sin x/x) 和 lim(1+1/x)^x 必须背熟。",
         "keywords": ["极限", "ε-δ定义", "四则运算", "重要极限", "夹逼准则", "单调有界准则"]},
        {"id": "F03", "name": "无穷小与无穷大", "chapter": "第一章 函数与极限", "difficulty": 2,
         "concept": "无穷小是以零为极限的量。掌握无穷小的比较（高阶、同阶、等价）、等价无穷小替换和无穷大的概念。",
         "common_exams": ["比较两个无穷小的阶", "等价无穷小替换求极限", "确定无穷小的阶数"],
         "common_errors": "在加减运算中错误使用等价无穷小替换（仅在乘除中安全），混淆高阶和同阶的判断",
         "advice": "背熟8个常用等价无穷小（x→0时 sinx~x, tanx~x, lnx~x 等）。记住：等价替换只适用于乘除法，加减法中不能用。",
         "keywords": ["无穷小", "无穷大", "等价无穷小", "高阶", "同阶", "阶的比较"]},
        {"id": "F04", "name": "连续与间断", "chapter": "第一章 函数与极限", "difficulty": 2,
         "concept": "函数在某点连续需要满足三个条件：有定义、有极限、极限值等于函数值。间断点分为第一类（可去、跳跃）和第二类（无穷、振荡）。",
         "common_exams": ["判断函数在某点的连续性", "分类间断点类型", "利用闭区间上连续函数的性质证明"],
         "common_errors": "只验证极限存在就判断连续，忘记检查函数值是否等于极限值；间断点分类时混淆第一类和第二类",
         "advice": "连续的三要素（有定义、有极限、值相等）缺一不可。闭区间上连续函数的零点定理和介值定理是证明题的常用工具。",
         "keywords": ["连续", "间断点", "可去间断", "跳跃间断", "无穷间断", "零点定理", "介值定理"]},
        # 第二章
        {"id": "D01", "name": "导数的定义", "chapter": "第二章 导数与微分", "difficulty": 2,
         "concept": "导数是函数增量与自变量增量之比在增量趋近零时的极限，几何意义是切线斜率。掌握左导数、右导数和可导与连续的关系。",
         "common_exams": ["用定义求导数", "判断函数在某点的可导性", "讨论可导与连续的关系"],
         "common_errors": "混淆导数定义的两种等价形式，在分段函数分界点忘记用定义求导",
         "advice": "记住：可导必连续，但连续不一定可导（如 |x| 在 x=0 处）。分段函数在分界点必须用左导数和右导数分别判断。",
         "keywords": ["导数定义", "左导数", "右导数", "可导", "连续", "切线斜率", "变化率"]},
        {"id": "D02", "name": "基本求导公式", "chapter": "第二章 导数与微分", "difficulty": 1,
         "concept": "掌握基本初等函数的导数公式：幂函数、指数函数、对数函数、三角函数、反三角函数的求导公式，以及导数的四则运算法则。",
         "common_exams": ["利用公式和四则运算求导", "求多项式/分式的导数", "三角函数求导"],
         "common_errors": "混淆 (sinx)'=cosx 和 (cosx)'=-sinx；忘记除法法则中分母的平方；对数求导忘记取对数后的步骤",
         "advice": "导数公式表必须烂熟于心。建议每天默写一遍，特别留心负号（cosx、cotx 的导数带负号）。",
         "keywords": ["导数公式", "四则运算", "幂函数", "指数函数", "对数函数", "三角函数", "反三角函数"]},
        {"id": "D03", "name": "复合函数求导", "chapter": "第二章 导数与微分", "difficulty": 2,
         "concept": "链式法则：复合函数的导数等于外层函数对中间变量的导数乘以中间变量对自变量的导数。是高数中最核心的求导技巧。",
         "common_exams": ["多层复合函数求导", "与四则运算混合的求导", "抽象复合函数求导"],
         "common_errors": "漏掉链式法则中的某一环（多层复合时少乘一步），混淆中间变量和自变量",
         "advice": "求导时从外到内一层一层剥，每剥一层乘一个导数。建议先设中间变量 u=...，写清楚每一步，熟练后省略。",
         "keywords": ["链式法则", "复合函数", "中间变量", "多层复合"]},
        {"id": "D04", "name": "隐函数求导", "chapter": "第二章 导数与微分", "difficulty": 2,
         "concept": "对不能显式解出 y 的方程 F(x,y)=0，对方程两边同时对 x 求导，注意 y 是 x 的函数，需要用链式法则处理 y 的项。",
         "common_exams": ["隐函数求 dy/dx", "对数求导法", "参数方程确定的函数求导"],
         "common_errors": "对 y 的项忘记乘 dy/dx；对数求导时忘记对加项分别取对数",
         "advice": "隐函数求导的核心：看到 y 就多乘一个 y'。对数求导法适用于幂指函数 y=f(x)^g(x) 和多个因式相乘除的情况。",
         "keywords": ["隐函数", "对数求导法", "参数方程", "幂指函数"]},
        {"id": "D05", "name": "高阶导数", "chapter": "第二章 导数与微分", "difficulty": 3,
         "concept": "高阶导数是导数的导数。掌握莱布尼茨公式、常见函数的 n 阶导数公式和递推法求高阶导数。",
         "common_exams": ["求函数的 n 阶导数", "利用莱布尼茨公式", "求指定点的高阶导数值"],
         "common_errors": "求高阶导数时找规律不严谨，未用数学归纳法验证；莱布尼茨公式中组合数搞错",
         "advice": "先算前几阶找规律，再用归纳法证明。记住 sinx 和 cosx 的 n 阶导数公式（周期为4），以及 1/(ax+b) 的 n 阶导数公式。",
         "keywords": ["高阶导数", "莱布尼茨公式", "递推法", "数学归纳法"]},
        {"id": "D06", "name": "微分及其应用", "chapter": "第二章 导数与微分", "difficulty": 2,
         "concept": "微分 dy=f'(x)dx 是函数增量的线性主部。掌握微分的几何意义、微分形式的不变性和近似计算应用。",
         "common_exams": ["求函数的微分", "利用微分做近似计算", "微分在误差估计中的应用"],
         "common_errors": "混淆导数和微分的概念；近似计算中忽略高阶无穷小项的影响",
         "advice": "微分的关键理解：dy≈Δy，误差是 o(Δx)。微分形式不变性意味着不论 u 是自变量还是中间变量，dy=f'(u)du 都成立。",
         "keywords": ["微分", "线性主部", "近似计算", "误差估计", "微分形式不变性"]},
        # 第三章
        {"id": "M01", "name": "中值定理", "chapter": "第三章 微分中值定理与导数应用", "difficulty": 3,
         "concept": "罗尔定理、拉格朗日中值定理、柯西中值定理是导数应用的理论基础。核心思想：函数在区间上的平均变化率等于某点的瞬时变化率。",
         "common_exams": ["用中值定理证明等式", "证明方程根的存在性", "证明不等式"],
         "common_errors": "不验证定理条件就使用（如忘记验证连续性和可导性）；构造辅助函数不当",
         "advice": "证明题的关键是构造合适的辅助函数。罗尔定理最常用于证明方程有根；拉格朗日用于证明不等式。多积累辅助函数的构造技巧。",
         "keywords": ["罗尔定理", "拉格朗日中值定理", "柯西中值定理", "辅助函数", "证明"]},
        {"id": "M02", "name": "洛必达法则", "chapter": "第三章 微分中值定理与导数应用", "difficulty": 2,
         "concept": "用于求 0/0 型和 ∞/∞ 型未定式极限，通过对分子分母分别求导来化简。可连续使用，但每次使用前必须验证是否为未定式。",
         "common_exams": ["0/0 型极限", "∞/∞ 型极限", "其他类型转化为基本型（0·∞、∞-∞、1^∞、0^0、∞^0）"],
         "common_errors": "不验证未定式类型就直接用；使用后不化简导致越求越复杂；忽略等价无穷小可能更简单",
         "advice": "洛必达法则不是万能的。先用等价无穷小化简，再决定是否用洛必达。每次求导后先化简再判断是否需要继续。",
         "keywords": ["洛必达法则", "0/0型", "∞/∞型", "未定式", "等价无穷小"]},
        {"id": "M03", "name": "泰勒公式", "chapter": "第三章 微分中值定理与导数应用", "difficulty": 3,
         "concept": "用多项式逼近函数：f(x)=f(x0)+f'(x0)(x-x0)+...+f^(n)(x0)/n!·(x-x0)^n+Rn。掌握常见函数的麦克劳林展开和佩亚诺余项、拉格朗日余项。",
         "common_exams": ["求函数的泰勒展开", "用泰勒公式求极限", "用泰勒公式证明不等式", "近似计算与误差估计"],
         "common_errors": "记错展开式系数；余项写错；求极限时展开阶数不够导致误判",
         "advice": "必须背熟 5 个基本展开：e^x、sinx、cosx、ln(1+x)、(1+x)^α。求极限时展开到分子分母同阶，多展开一两阶保险。",
         "keywords": ["泰勒公式", "麦克劳林公式", "佩亚诺余项", "拉格朗日余项", "多项式逼近"]},
        {"id": "M04", "name": "函数单调性与极值", "chapter": "第三章 微分中值定理与导数应用", "difficulty": 2,
         "concept": "利用一阶导数的符号判断单调性：f'>0 递增，f'<0 递减。极值的必要条件是 f'=0 或不存在，充分条件用一阶导数变号或二阶导数判断。",
         "common_exams": ["求函数单调区间", "求极值和极值点", "证明不等式（利用单调性）"],
         "common_errors": "忘记检查导数不存在的点；二阶导数判别法在 f''=0 时失效却仍使用",
         "advice": "求极值的标准流程：1)求 f' 2)找可疑点（f'=0 或不存在）3)用一阶导数变号法判断。二阶导数判别法只适用于 f'=0 且 f''≠0 的点。",
         "keywords": ["单调性", "极值", "极值点", "一阶导数", "二阶导数判别", "驻点"]},
        {"id": "M05", "name": "函数最值与凹凸性", "chapter": "第三章 微分中值定理与导数应用", "difficulty": 2,
         "concept": "最值在驻点和端点中比较；凹凸性用二阶导数判断：f''>0 凹，f''<0 凸。拐点是凹凸性改变的点，必要条件是 f''=0 或不存在。",
         "common_exams": ["求闭区间上函数的最值", "求凹凸区间和拐点", "利用凹凸性证明不等式"],
         "common_errors": "混淆极值和最值；拐点写成 x 坐标而不是点 (x,f(x))；忘记验证 f'' 变号",
         "advice": "最值要比较所有驻点和端点的函数值。拐点必须满足二阶导数变号，f''=0 只是必要条件。画函数图像时先标单调性再标凹凸性。",
         "keywords": ["最大值", "最小值", "凹凸性", "拐点", "二阶导数", "渐近线"]},
        # 第四章
        {"id": "I01", "name": "不定积分概念", "chapter": "第四章 不定积分", "difficulty": 2,
         "concept": "不定积分是求导的逆运算。掌握原函数的概念、基本积分公式和线性性质。注意不定积分的结果带任意常数 C。",
         "common_exams": ["用基本公式求积分", "利用线性性质拆分积分", "验证积分结果是否正确"],
         "common_errors": "忘记加常数 C；把积分公式和导数公式搞混；不验证结果是否正确",
         "advice": "积分是求导的逆运算，所以验证方法就是对结果求导看是否回到被积函数。基本积分公式必须背熟，它们是所有积分技巧的基础。",
         "keywords": ["不定积分", "原函数", "基本积分公式", "线性性质", "任意常数"]},
        {"id": "I02", "name": "换元积分法", "chapter": "第四章 不定积分", "difficulty": 3,
         "concept": "通过变量替换化简积分。第一类换元（凑微分）：将 f(g(x))g'(x)dx 凑成 f(u)du；第二类换元：设 x=φ(t) 化简被积函数。",
         "common_exams": ["凑微分法求积分", "三角换元（x=asint, x=atant）", "根式换元"],
         "common_errors": "凑微分时方向搞反；换元后忘记回代；三角换元时忘记定义域限制导致符号错误",
         "advice": "凑微分法的核心是识别复合结构。常见的凑微分：e^x dx → d(e^x)，x dx → d(x²/2)，1/x dx → d(lnx)。三角换元用于消除根号。",
         "keywords": ["换元积分", "凑微分", "第一类换元", "第二类换元", "三角换元", "根式换元"]},
        {"id": "I03", "name": "分部积分法", "chapter": "第四章 不定积分", "difficulty": 3,
         "concept": "分部积分公式：∫u dv = uv - ∫v du。适用于被积函数是两类函数乘积的情况。选 u 的口诀：反对幂指三（从前往后选 u）。",
         "common_exams": ["多项式×指数函数的积分", "多项式×三角函数的积分", "多项式×对数函数的积分"],
         "common_errors": "u 和 dv 选错导致越积越复杂；循环积分时方程列错；忘记分部积分后仍需积分剩余部分",
         "advice": "选 u 的原则：求导后变简单的选 u。多项式×指数→选多项式为 u；多项式×对数→选对数为 u。循环积分（如 ∫e^x·sinx dx）要设方程求解。",
         "keywords": ["分部积分", "反对幂指三", "循环积分", "LIATE法则"]},
        {"id": "I04", "name": "有理函数积分", "chapter": "第四章 不定积分", "difficulty": 3,
         "concept": "将有理函数分解为部分分式后逐项积分。掌握假分式化真分式、真分式的部分分式分解（一次因式、二次不可约因式）。",
         "common_exams": ["有理分式的积分", "三角有理式积分（万能代换）", "简单无理函数积分"],
         "common_errors": "部分分式分解系数算错；忘记讨论分母是否有重根或共轭复根；万能代换后化简不当",
         "advice": "部分分式分解是机械操作但容易算错。先检查是否为真分式（不是则先除），再根据分母因式类型设分式。三角有理式用 t=tan(x/2) 万能代换。",
         "keywords": ["有理函数", "部分分式", "真分式", "假分式", "万能代换", "无理函数积分"]},
        # 第五章
        {"id": "DI01", "name": "定积分概念与性质", "chapter": "第五章 定积分", "difficulty": 2,
         "concept": "定积分是分割、求和、取极限的过程，几何意义是曲线下面积。掌握定积分的性质（线性性、可加性、保号性、积分中值定理）。",
         "common_exams": ["利用定积分性质比较大小", "积分中值定理的应用", "估计定积分的值"],
         "common_errors": "混淆定积分和不定积分（定积分是数，不定积分是函数）；忽略积分上下限的大小关系",
         "advice": "定积分的值只与被积函数和积分区间有关，与积分变量符号无关。积分中值定理在证明题中经常用到。",
         "keywords": ["定积分", "分割求和取极限", "积分中值定理", "线性性", "可加性", "保号性"]},
        {"id": "DI02", "name": "微积分基本定理", "chapter": "第五章 定积分", "difficulty": 2,
         "concept": "牛顿-莱布尼茨公式：∫a^b f(x)dx = F(b)-F(a)，其中 F 是 f 的原函数。变上限积分 Φ(x)=∫a^x f(t)dt 的导数是 f(x)。",
         "common_exams": ["求变上限积分的导数", "利用牛顿-莱布尼茨公式计算定积分", "变上限积分的极限问题"],
         "common_errors": "求变上限积分导数时忘记链式法则（上限是 x 的函数时）；上下限搞反",
         "advice": "变上限积分求导公式：d/dx ∫a^x f(t)dt = f(x)。如果上限是 g(x)，则要乘 g'(x)。这是考研高频考点。",
         "keywords": ["牛顿-莱布尼茨公式", "变上限积分", "原函数存在定理", "微积分基本定理"]},
        {"id": "DI03", "name": "定积分计算", "chapter": "第五章 定积分", "difficulty": 2,
         "concept": "利用换元法和分部积分法计算定积分，注意换元时必须同时变换上下限。掌握奇偶函数在对称区间上的积分性质和周期函数的积分性质。",
         "common_exams": ["定积分的换元法", "定积分的分部积分", "利用对称性简化计算", "分段函数的定积分"],
         "common_errors": "定积分换元后忘记换上下限；忽略被积函数的奇偶性导致计算复杂；分段函数在分界点没有分段积分",
         "advice": "计算前先观察：奇函数在对称区间积分为零，偶函数可以只算一半再乘2。这是简化计算的关键技巧。",
         "keywords": ["定积分换元", "定积分分部积分", "奇偶性", "周期性", "对称区间"]},
        {"id": "DI04", "name": "反常积分", "chapter": "第五章 定积分", "difficulty": 3,
         "concept": "反常积分分为无穷限积分（积分区间无限）和无界函数积分（被积函数在某点无界）。通过取极限来判断收敛或发散。",
         "common_exams": ["判断反常积分收敛/发散", "计算反常积分的值", "比较判别法判断收敛性"],
         "common_errors": "把无界函数积分当普通定积分计算；p-积分的收敛条件记混（p>1 收敛 vs p<1 收敛）",
         "advice": "无穷限反常积分：p>1 收敛。无界函数反常积分（在端点无界）：p<1 收敛。这两个条件恰好相反，容易混淆，要特别记忆。",
         "keywords": ["反常积分", "无穷限积分", "无界函数积分", "收敛", "发散", "p-积分", "比较判别法"]},
        # 第六章
        {"id": "DI05", "name": "定积分应用（面积体积）", "chapter": "第六章 定积分应用", "difficulty": 2,
         "concept": "用定积分求平面图形面积（直角坐标和极坐标）、旋转体体积（切片法、 shells法）、平行截面面积已知的立体体积。",
         "common_exams": ["求两曲线围成的面积", "求旋转体体积", "极坐标下求面积"],
         "common_errors": "面积积分时上下函数搞反（结果为负）；旋转轴不是坐标轴时没有平移调整；极坐标面积公式中忘记乘 1/2",
         "advice": "面积公式：∫(上-下)dx 或 ∫(右-左)dy。旋转体体积：绕 x 轴用 π∫f²dx，绕 y 轴用 2π∫xf(x)dx（shell法）。先画图确定积分区域。",
         "keywords": ["面积", "体积", "旋转体", "切片法", "shell法", "极坐标面积"]},
        {"id": "DI06", "name": "定积分应用（弧长物理）", "chapter": "第六章 定积分应用", "difficulty": 3,
         "concept": "求平面曲线弧长（直角坐标、参数方程、极坐标）、变力做功、液体侧压力、引力等物理应用。",
         "common_exams": ["求曲线弧长", "变力沿直线做功", "水压力计算"],
         "common_errors": "弧长公式中参数方程忘记乘 dt/dt 项；物理应用中坐标系建立不当导致积分复杂",
         "advice": "弧长公式三种形式要分清：直角坐标 ∫√(1+y'²)dx，参数方程 ∫√(x'²+y'²)dt，极坐标 ∫√(r²+r'²)dθ。物理问题关键是正确建系。",
         "keywords": ["弧长", "变力做功", "水压力", "引力", "参数方程弧长", "极坐标弧长"]},
        # 第七章
        {"id": "D07", "name": "多元函数偏导数", "chapter": "第七章 多元函数微分", "difficulty": 2,
         "concept": "偏导数是多元函数对一个变量求导时把其他变量当常数。掌握偏导数的定义、计算和几何意义。",
         "common_exams": ["求一阶/二阶偏导数", "验证混合偏导相等", "分段函数在分界点的偏导数"],
         "common_errors": "求偏导时没有真正把其他变量当常数；二阶混合偏导求导顺序错误",
         "advice": "偏导数本质上就是一元函数的导数。求 fx 时把 y、z 当常数处理。二阶混合偏导在连续条件下与求导顺序无关（Clairaut定理）。",
         "keywords": ["偏导数", "多元函数", "混合偏导", "Clairaut定理", "二阶偏导"]},
        {"id": "D08", "name": "全微分", "chapter": "第七章 多元函数微分", "difficulty": 2,
         "concept": "全微分 dz=fx dx+fy dy 是函数全增量的线性主部。掌握可微的必要条件（偏导存在）和充分条件（偏导连续）。",
         "common_exams": ["求函数的全微分", "判断函数是否可微", "近似计算"],
         "common_errors": "混淆可偏导和可微（可偏导不一定可微）；判断可微时忘记检查极限是否为零",
         "advice": "可微关系链：偏导连续→可微→偏导存在→连续。判断可微的关键：检查 Δz-fxΔx-fyΔy 是否是 ρ 的高阶无穷小。",
         "keywords": ["全微分", "可微", "全增量", "线性主部", "偏导连续"]},
        {"id": "D09", "name": "多元复合函数求导", "chapter": "第七章 多元函数微分", "difficulty": 3,
         "concept": "多元复合函数链式法则：通过画变量依赖关系图（树图）来确定求导路径。每条路径对应一个偏导项的乘积。",
         "common_exams": ["多元复合函数求偏导", "抽象复合函数求导", "全微分形式不变性应用"],
         "common_errors": "树图画错导致链式法则缺项或多项；对中间变量和自变量混淆",
         "advice": "先画树图：因变量→中间变量→自变量。从因变量到每个自变量的每条路径上，把各段偏导相乘，再把各路径的结果相加。",
         "keywords": ["链式法则", "多元复合函数", "树图", "中间变量", "全微分形式不变性"]},
        {"id": "D10", "name": "隐函数求导（多元）", "chapter": "第七章 多元函数微分", "difficulty": 3,
         "concept": "由 F(x,y,z)=0 确定的隐函数 z=f(x,y) 的偏导数：∂z/∂x=-Fx/Fz, ∂z/∂y=-Fy/Fz。掌握隐函数存在定理。",
         "common_exams": ["求隐函数的偏导数", "方程组确定的隐函数求导", "验证隐函数存在定理条件"],
         "common_errors": "公式中分子分母搞反；忘记验证 Fz≠0 的条件；方程组情况不会用雅可比行列式",
         "advice": "隐函数偏导公式口诀：对谁求偏导，谁放分母；其他变量放分子，带负号。方程组情况用克拉默法则更方便。",
         "keywords": ["隐函数", "偏导数", "隐函数存在定理", "雅可比行列式", "克拉默法则"]},
        # 第八章
        {"id": "DI07", "name": "二重积分", "chapter": "第八章 重积分", "difficulty": 3,
         "concept": "二重积分是二元函数在平面区域上的积分，几何意义是曲顶柱体体积。掌握直角坐标和极坐标下的计算方法，关键是确定积分限。",
         "common_exams": ["直角坐标下计算二重积分", "极坐标下计算二重积分", "交换积分次序", "利用对称性简化"],
         "common_errors": "积分限确定错误（特别是交换次序后）；该用极坐标的用了直角坐标（圆形区域）；忽略对称性导致计算复杂",
         "advice": "画图确定积分区域是第一步。圆形/扇形区域用极坐标，矩形/三角形用直角坐标。交换次序时必须重新画图确定新积分限。",
         "keywords": ["二重积分", "直角坐标", "极坐标", "交换积分次序", "对称性", "曲顶柱体"]},
        {"id": "DI08", "name": "三重积分", "chapter": "第八章 重积分", "difficulty": 3,
         "concept": "三重积分是三元函数在空间区域上的积分。掌握直角坐标、柱坐标和球坐标下的计算方法，关键是根据区域形状选择坐标系。",
         "common_exams": ["直角坐标下计算三重积分", "柱坐标计算", "球坐标计算", "选择合适的坐标系"],
         "common_errors": "坐标系选择不当（球形区域用了直角坐标）；球坐标体积元素忘记 Jacobi 行列式；积分限错误",
         "advice": "选坐标系看区域形状：柱形用柱坐标，球形用球坐标，长方体用直角坐标。球坐标体积元素 = r²sinφ dr dφ dθ，必须记住。",
         "keywords": ["三重积分", "柱坐标", "球坐标", "体积元素", "Jacobi行列式"]},
        # 第九章
        {"id": "DI09", "name": "曲线积分", "chapter": "第九章 曲线积分与曲面积分", "difficulty": 3,
         "concept": "第一类曲线积分（对弧长）与弧长有关，第二类曲线积分（对坐标）与方向有关。掌握格林公式：∮L Pdx+Qdy=∬D(∂Q/∂x-∂P/∂y)dA。",
         "common_exams": ["计算第一类曲线积分", "计算第二类曲线积分", "格林公式应用", "判断曲线积分与路径无关"],
         "common_errors": "第一类和第二类搞混；格林公式忘记验证条件（闭合曲线+正向）；路径无关条件使用不当",
         "advice": "格林公式是核心：把曲线积分转化为二重积分。路径无关的四个等价条件必须背熟：∂Q/∂x=∂P/∂y、沿任意闭曲线积分为零、积分与路径无关、Pdx+Qdy 是某函数的全微分。",
         "keywords": ["曲线积分", "第一类", "第二类", "格林公式", "路径无关", "全微分"]},
        {"id": "DI10", "name": "曲面积分", "chapter": "第九章 曲线积分与曲面积分", "difficulty": 3,
         "concept": "第一类曲面积分（对面积）和第二类曲面积分（对坐标）。掌握高斯公式（散度定理）和斯托克斯公式，联系曲面积分与三重积分/曲线积分。",
         "common_exams": ["计算曲面积分", "高斯公式应用", "斯托克斯公式应用"],
         "common_errors": "高斯公式条件验证不足（封闭曲面+外侧）；法向量方向搞错；斯托克斯公式中曲面选择不当",
         "advice": "高斯公式把闭曲面积分转化为三重积分，是最常用的工具。非闭曲面可以先补面再减去。斯托克斯公式用于把空间曲线积分转化为曲面积分。",
         "keywords": ["曲面积分", "高斯公式", "斯托克斯公式", "散度定理", "法向量"]},
        # 第十章
        {"id": "DI11", "name": "常数项级数", "chapter": "第十章 无穷级数", "difficulty": 3,
         "concept": "级数收敛的必要条件是通项趋近于零。掌握正项级数的比较判别法、比值判别法、根值判别法，以及交错级数的莱布尼茨判别法。",
         "common_exams": ["判断级数收敛/发散", "比值法和根值法的应用", "交错级数收敛性判断"],
         "common_errors": "通项趋于零就判断收敛（这是必要非充分条件）；比较判别法中不等式方向搞反",
         "advice": "判断流程：1)先看通项是否趋于零（不趋于零必发散）2)正项级数用比值法 3)交错级数用莱布尼茨法 4)以上不行用比较法。p-级数（1/n^p）是常用比较标准。",
         "keywords": ["级数", "收敛", "发散", "比值法", "根值法", "比较判别法", "莱布尼茨判别法", "p-级数"]},
        {"id": "DI12", "name": "幂级数", "chapter": "第十章 无穷级数", "difficulty": 3,
         "concept": "幂级数 ∑aₙxⁿ 的收敛域和收敛半径。掌握阿贝尔定理、幂级数的分析运算（逐项求导/积分）和函数的幂级数展开。",
         "common_exams": ["求幂级数收敛半径和收敛域", "函数展开为幂级数", "利用幂级数求常数项级数的和"],
         "common_errors": "收敛区间端点忘记单独判断；逐项求导/积分后收敛半径不变但端点可能变化",
         "advice": "收敛半径 R=lim|aₙ/aₙ₊₁|（比值法）或 R=limⁿ√|aₙ|（根值法）。端点必须代入单独判断收敛性。常用展开式要背熟。",
         "keywords": ["幂级数", "收敛半径", "收敛域", "阿贝尔定理", "逐项求导", "逐项积分", "泰勒展开"]},
        {"id": "DI13", "name": "傅里叶级数", "chapter": "第十章 无穷级数", "difficulty": 3,
         "concept": "将周期函数展开为三角级数。掌握傅里叶系数公式、狄利克雷收敛定理和奇偶延拓。周期2π和周期2l的展开。",
         "common_exams": ["求函数的傅里叶级数", "利用帕塞瓦尔等式求级数和", "正弦级数和余弦级数"],
         "common_errors": "傅里叶系数公式中积分区间搞错；奇偶延拓后忘记对应的级数类型；狄利克雷条件验证不全",
         "advice": "傅里叶系数：aₙ=(1/π)∫f(x)cos(nx)dx, bₙ=(1/π)∫f(x)sin(nx)dx。奇函数只有正弦项，偶函数只有余弦项。狄利克雷定理保证收敛到 (f(x+)+f(x-))/2。",
         "keywords": ["傅里叶级数", "傅里叶系数", "狄利克雷定理", "正弦级数", "余弦级数", "奇偶延拓", "帕塞瓦尔等式"]},
        # 第十一章
        {"id": "DI14", "name": "一阶微分方程", "chapter": "第十一章 微分方程", "difficulty": 2,
         "concept": "掌握可分离变量方程、齐次方程、一阶线性微分方程（常数变易法/积分因子法）和伯努利方程的解法。",
         "common_exams": ["解可分离变量方程", "解一阶线性微分方程", "齐次方程的变量替换"],
         "common_errors": "分离变量时忘记讨论分母为零的情况；一阶线性方程公式中 P(x) 和 Q(x) 的位置搞混",
         "advice": "一阶线性方程 y'+P(x)y=Q(x) 的通解公式：y=e^(-∫Pdx)[∫Qe^(∫Pdx)dx+C]。必须背熟。识别方程类型是解题第一步：先看能否分离变量，再看是否齐次，再看是否线性。",
         "keywords": ["微分方程", "可分离变量", "齐次方程", "一阶线性", "伯努利方程", "常数变易法"]},
        {"id": "DI15", "name": "高阶微分方程", "chapter": "第十一章 微分方程", "difficulty": 3,
         "concept": "掌握可降阶方程（y''=f(x)、y''=f(x,y')、y''=f(y,y')）、二阶常系数齐次/非齐次线性微分方程的解法。",
         "common_exams": ["可降阶方程的求解", "二阶常系数齐次方程（特征方程法）", "二阶常系数非齐次方程（待定系数法）"],
         "common_errors": "特征方程的根的三种情况对应的通解形式记混；非齐次方程特解的形式设错",
         "advice": "特征方程 r²+pr+q=0：1)两个不等实根→C₁e^r₁x+C₂e^r₂x 2)重根→(C₁+C₂x)e^rx 3)复根α±βi→e^αx(C₁cosβx+C₂sinβx)。非齐次特解：右端是多项式设多项式，是指数设指数，是三角设三角。",
         "keywords": ["高阶微分方程", "可降阶", "特征方程", "常系数", "齐次", "非齐次", "待定系数法"]},
    ],
    "edges": [
        # 第一章内部
        {"from": "F01", "to": "F02"},
        {"from": "F02", "to": "F03"},
        {"from": "F03", "to": "F04"},
        # 第一章→第二章
        {"from": "F02", "to": "D01"},
        {"from": "F04", "to": "D01"},
        # 第二章内部
        {"from": "D01", "to": "D02"},
        {"from": "D02", "to": "D03"},
        {"from": "D03", "to": "D04"},
        {"from": "D03", "to": "D05"},
        {"from": "D02", "to": "D06"},
        # 第二章→第三章
        {"from": "D02", "to": "M01"},
        {"from": "D03", "to": "M01"},
        {"from": "M01", "to": "M02"},
        {"from": "M01", "to": "M03"},
        {"from": "D05", "to": "M03"},
        {"from": "M02", "to": "M04"},
        {"from": "M04", "to": "M05"},
        # 第三章→第四章
        {"from": "D06", "to": "I01"},
        {"from": "D02", "to": "I01"},
        {"from": "I01", "to": "I02"},
        {"from": "I02", "to": "I03"},
        {"from": "I03", "to": "I04"},
        # 第四章→第五章
        {"from": "I01", "to": "DI01"},
        {"from": "DI01", "to": "DI02"},
        {"from": "I02", "to": "DI03"},
        {"from": "I03", "to": "DI03"},
        {"from": "DI02", "to": "DI03"},
        {"from": "DI03", "to": "DI04"},
        # 第五章→第六章
        {"from": "DI03", "to": "DI05"},
        {"from": "DI03", "to": "DI06"},
        # 第二章→第七章
        {"from": "D03", "to": "D07"},
        {"from": "D07", "to": "D08"},
        {"from": "D03", "to": "D09"},
        {"from": "D07", "to": "D09"},
        {"from": "D09", "to": "D10"},
        {"from": "D04", "to": "D10"},
        # 第五章→第八章
        {"from": "DI05", "to": "DI07"},
        {"from": "DI07", "to": "DI08"},
        # 第八章→第九章
        {"from": "DI07", "to": "DI09"},
        {"from": "DI08", "to": "DI10"},
        # 第五章→第十章
        {"from": "DI04", "to": "DI11"},
        {"from": "DI11", "to": "DI12"},
        {"from": "M03", "to": "DI12"},
        {"from": "DI12", "to": "DI13"},
        # 第三章→第十一章
        {"from": "D01", "to": "DI14"},
        {"from": "DI14", "to": "DI15"},
        {"from": "D05", "to": "DI15"},
    ]
}


def get_knowledge_graph():
    """获取知识点图谱数据，含后续知识点和练习统计"""
    import copy
    graph = copy.deepcopy(KNOWLEDGE_GRAPH)

    # 构建 id→node 映射
    node_map = {n["id"]: n for n in graph["nodes"]}

    # 为每个节点添加 successors（后续知识点）
    for edge in graph["edges"]:
        src = edge["from"]
        tgt = edge["to"]
        if src in node_map:
            if "successors" not in node_map[src]:
                node_map[src]["successors"] = []
            tgt_node = node_map.get(tgt)
            if tgt_node:
                node_map[src]["successors"].append({
                    "id": tgt_node["id"],
                    "name": tgt_node["name"],
                    "chapter": tgt_node["chapter"]
                })

    # 为每个节点添加 prerequisites（直接前置）
    for edge in graph["edges"]:
        src = edge["from"]
        tgt = edge["to"]
        if tgt in node_map:
            if "prerequisites" not in node_map[tgt]:
                node_map[tgt]["prerequisites"] = []
            src_node = node_map.get(src)
            if src_node:
                node_map[tgt]["prerequisites"].append({
                    "id": src_node["id"],
                    "name": src_node["name"],
                    "chapter": src_node["chapter"]
                })

    return graph


def get_prerequisites(kp_name):
    """根据知识点名称找出所有前置知识点"""
    node = None
    for n in KNOWLEDGE_GRAPH["nodes"]:
        if n["name"] == kp_name or kp_name in n["name"]:
            node = n
            break
    if not node:
        return []

    visited = set()
    result = []
    def _find_prereqs(nid):
        for edge in KNOWLEDGE_GRAPH["edges"]:
            if edge["to"] == nid and edge["from"] not in visited:
                visited.add(edge["from"])
                for n in KNOWLEDGE_GRAPH["nodes"]:
                    if n["id"] == edge["from"]:
                        result.append(n)
                _find_prereqs(edge["from"])
    _find_prereqs(node["id"])
    return result
