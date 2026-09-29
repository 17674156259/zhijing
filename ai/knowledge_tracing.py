"""
贝叶斯知识追踪 (BKT)
=====================
基于学生练习记录动态估计知识点掌握度。

BKT 四参数模型:
- P(L0): 初始掌握概率（先验）
- P(T):  每次练习后从未掌握→掌握的转移概率
- P(G):  未掌握但猜对的概率（猜测）
- P(S):  掌握但做错的概率（失误）

更新公式:
  P(L_t | 正确) = P(L_t) * (1-P(S)) / (P(L_t)*(1-P(S)) + (1-P(L_t))*P(G))
  P(L_{t+1}) = P(L_t | 观察) + (1 - P(L_t | 观察)) * P(T)

  P(L_t | 错误) = P(L_t) * P(S) / (P(L_t)*P(S) + (1-P(L_t))*(1-P(G)))
  P(L_{t+1}) = P(L_t | 观察) + (1 - P(L_t | 观察)) * P(T)
"""

from models.database import get_db
from utils.logger import logger

# 默认 BKT 参数（按学科难度可调）
DEFAULT_PARAMS = {
    "P_L0": 0.3,   # 初始掌握概率 30%
    "P_T":  0.15,  # 每次练习转移概率 15%
    "P_G":  0.2,   # 猜测概率 20%
    "P_S":  0.1,   # 失误概率 10%
}


def get_knowledge_state(user_id: int, knowledge_point: str, subject: str = "高等数学") -> dict:
    """获取某知识点的当前掌握状态"""
    db = get_db()
    row = db.execute(
        "SELECT * FROM knowledge_state WHERE user_id=? AND knowledge_point=? AND subject=?",
        (user_id, knowledge_point, subject)
    ).fetchone()
    db.close()

    if row:
        return dict(row)

    # 初始化：使用默认参数
    return {
        "user_id": user_id,
        "knowledge_point": knowledge_point,
        "subject": subject,
        "p_learn": DEFAULT_PARAMS["P_L0"],
        "practice_count": 0,
        "correct_count": 0,
    }


def update_knowledge_state(user_id: int, knowledge_point: str, subject: str, is_correct: bool) -> float:
    """
    根据练习结果更新掌握度，返回新的 P(L)。
    """
    state = get_knowledge_state(user_id, knowledge_point, subject)
    p_learn = state.get("p_learn", DEFAULT_PARAMS["P_L0"])
    practice_count = state.get("practice_count", 0)
    correct_count = state.get("correct_count", 0)

    # BKT 更新
    p_t = DEFAULT_PARAMS["P_T"]
    p_g = DEFAULT_PARAMS["P_G"]
    p_s = DEFAULT_PARAMS["P_S"]

    if is_correct:
        p_learn_given = (p_learn * (1 - p_s)) / (
            p_learn * (1 - p_s) + (1 - p_learn) * p_g
        )
    else:
        p_learn_given = (p_learn * p_s) / (
            p_learn * p_s + (1 - p_learn) * (1 - p_g)
        )

    # 转移：本次练习后可能从未掌握→掌握
    p_learn_new = p_learn_given + (1 - p_learn_given) * p_t

    # 上限保护
    p_learn_new = min(p_learn_new, 0.99)

    # 写入数据库
    db = get_db()
    db.execute("""
        INSERT INTO knowledge_state (user_id, knowledge_point, subject, p_learn, practice_count, correct_count, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(user_id, knowledge_point, subject)
        DO UPDATE SET p_learn=?, practice_count=?, correct_count=?, updated_at=datetime('now')
    """, (user_id, knowledge_point, subject, p_learn_new,
          practice_count + 1, correct_count + (1 if is_correct else 0),
          p_learn_new, practice_count + 1, correct_count + (1 if is_correct else 0)))
    db.commit()
    db.close()

    logger.info(f"BKT更新: user={user_id}, kp={knowledge_point}, correct={is_correct}, P(L)={p_learn:.3f}→{p_learn_new:.3f}")
    return p_learn_new


def get_user_mastery_map(user_id: int, subject: str = None) -> dict:
    """获取用户所有知识点的掌握度映射"""
    db = get_db()
    if subject:
        rows = db.execute(
            "SELECT knowledge_point, subject, p_learn, practice_count, correct_count FROM knowledge_state WHERE user_id=? AND subject=?",
            (user_id, subject)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT knowledge_point, subject, p_learn, practice_count, correct_count FROM knowledge_state WHERE user_id=?",
            (user_id,)
        ).fetchall()
    db.close()

    return {
        f"{r['subject']}:{r['knowledge_point']}": {
            "mastery": round(r["p_learn"], 3),
            "practice_count": r["practice_count"],
            "correct_count": r["correct_count"],
        }
        for r in rows
    }
