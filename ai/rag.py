"""
RAG 知识库
==========
基于关键词检索的轻量 RAG，为 AI 诊断提供教材知识点参考。
不依赖 embedding 模型，使用 TF-IDF + 关键词匹配。
"""

import math
import re
from collections import Counter
from utils.logger import logger

# 教材知识点库（预置）
KNOWLEDGE_BASE = [
    {
        "subject": "高等数学",
        "topic": "链式法则",
        "content": "链式法则是复合函数求导的核心法则。若 y = f(g(x))，则 y' = f'(g(x)) · g'(x)。关键步骤：1) 识别外层函数 f 和内层函数 g；2) 分别求导；3) 相乘。常见错误：遗漏内层导数。例如 sin(x²) 的导数是 2x·cos(x²)，不是 cos(x²)。",
        "keywords": ["链式法则", "复合函数", "求导", "导数", "sin", "cos", "内层", "外层"],
    },
    {
        "subject": "高等数学",
        "topic": "换元积分法",
        "content": "换元积分法通过变量替换简化积分。第一类换元：∫f(g(x))g'(x)dx = ∫f(u)du，令 u=g(x)。第二类换元：三角换元、倒代换等。关键：换元后要回代。常见错误：忘记回代或换元不彻底。",
        "keywords": ["换元", "积分", "变量替换", "三角换元", "回代"],
    },
    {
        "subject": "高等数学",
        "topic": "分部积分法",
        "content": "分部积分公式：∫u dv = uv - ∫v du。选择 u 和 dv 的原则：LIATE（对数→反三角→代数→三角→指数）。常见错误：u 和 dv 选择不当导致积分更复杂。",
        "keywords": ["分部积分", "积分", "LIATE", "u", "dv"],
    },
    {
        "subject": "高等数学",
        "topic": "洛必达法则",
        "content": "洛必达法则用于求 0/0 或 ∞/∞ 型极限：lim f(x)/g(x) = lim f'(x)/g'(x)。前提：必须是未定式。常见错误：非未定式也用洛必达，或忘记验证条件。",
        "keywords": ["洛必达", "极限", "未定式", "0/0", "无穷"],
    },
    {
        "subject": "高等数学",
        "topic": "中值定理",
        "content": "罗尔定理：f(a)=f(b) 则存在 ξ 使 f'(ξ)=0。拉格朗日中值定理：f(b)-f(a)=f'(ξ)(b-a)。柯西中值定理：推广到两个函数。关键：验证连续性和可导性。",
        "keywords": ["中值定理", "罗尔", "拉格朗日", "柯西", "连续", "可导"],
    },
    {
        "subject": "线性代数",
        "topic": "矩阵的秩",
        "content": "矩阵的秩 = 行秩 = 列秩 = 非零子式的最高阶数。初等变换不改变秩。秩的用途：判断向量组线性相关性、方程组解的结构。rank(A) < n → 线性相关。",
        "keywords": ["秩", "矩阵", "初等变换", "线性相关", "子式"],
    },
    {
        "subject": "线性代数",
        "topic": "特征值与特征向量",
        "content": "Ax = λx，λ 为特征值，x 为特征向量。求法：解 |A-λI|=0 得特征值，解 (A-λI)x=0 得特征向量。性质：迹=特征值之和，行列式=特征值之积。",
        "keywords": ["特征值", "特征向量", "特征方程", "行列式", "迹"],
    },
    {
        "subject": "概率论与数理统计",
        "topic": "贝叶斯公式",
        "content": "P(A|B) = P(B|A)P(A)/P(B)。先验概率 P(A)，后验概率 P(A|B)。全概率公式：P(B) = ΣP(B|Ai)P(Ai)。常见错误：混淆先验和后验。",
        "keywords": ["贝叶斯", "条件概率", "先验", "后验", "全概率"],
    },
    {
        "subject": "概率论与数理统计",
        "topic": "中心极限定理",
        "content": "大量独立同分布随机变量之和近似服从正态分布。X̄ ≈ N(μ, σ²/n)。样本量越大越接近正态。应用：区间估计、假设检验。",
        "keywords": ["中心极限定理", "正态分布", "样本", "均值", "方差"],
    },
    {
        "subject": "大学物理",
        "topic": "牛顿运动定律",
        "content": "第一定律：惯性定律，不受力时保持静止或匀速直线运动。第二定律：F=ma。第三定律：作用力与反作用力大小相等方向相反。常见错误：混淆质量和重量。",
        "keywords": ["牛顿", "运动定律", "惯性", "力", "质量", "加速度"],
    },
]

# 构建倒排索引
_inverted_index: dict = {}
for entry in KNOWLEDGE_BASE:
    for kw in entry["keywords"]:
        if kw not in _inverted_index:
            _inverted_index[kw] = []
        _inverted_index[kw].append(entry)


def retrieve(question: str, student_answer: str, subject: str = "高等数学", top_k: int = 3) -> list:
    """
    根据题目内容检索相关知识点。

    Returns:
        [{"topic": ..., "content": ..., "score": ...}, ...]
    """
    query_text = f"{question} {student_answer}"

    # 关键词匹配打分
    scores: dict = {}
    for kw, entries in _inverted_index.items():
        if kw in query_text:
            for entry in entries:
                if entry["subject"] != subject:
                    continue
                eid = id(entry)
                scores[eid] = scores.get(eid, 0) + len(kw)

    # TF-IDF 补充打分
    query_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', query_text.lower()))
    for entry in KNOWLEDGE_BASE:
        if entry["subject"] != subject:
            continue
        eid = id(entry)
        entry_words = set(re.findall(r'[a-zA-Z\u4e00-\u9fff]+', entry["content"].lower()))
        overlap = len(query_words & entry_words)
        if overlap > 0:
            tf = overlap / len(query_words) if query_words else 0
            idf = math.log(len(KNOWLEDGE_BASE) / max(1, sum(1 for e in KNOWLEDGE_BASE if e["subject"] == subject)))
            scores[eid] = scores.get(eid, 0) + tf * idf * 2

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

    results = []
    for eid, score in ranked:
        for entry in KNOWLEDGE_BASE:
            if id(entry) == eid:
                results.append({
                    "topic": entry["topic"],
                    "content": entry["content"],
                    "score": round(score, 3),
                })
                break

    logger.info(f"RAG检索: subject={subject}, 命中{len(results)}条")
    return results


def build_rag_context(question: str, student_answer: str, subject: str = "高等数学") -> str:
    """检索相关知识点并构建上下文文本，注入到 AI 提示词中"""
    refs = retrieve(question, student_answer, subject)
    if not refs:
        return ""

    context = "\n\n## 教材知识参考（RAG 检索结果）\n"
    for i, ref in enumerate(refs, 1):
        context += f"\n### 参考{i}：{ref['topic']}\n{ref['content']}\n"
    context += "\n请在诊断中参考以上教材内容，确保分析准确。"
    return context
