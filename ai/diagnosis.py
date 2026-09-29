"""
AI 错题诊断模块（多学科版）
==========================
支持高等数学、线性代数、概率论、离散数学、大学物理等多学科。
"""

from ai.llm import chat_json, chat_stream
from ai.rag import build_rag_context


# ============================================================
#  各学科知识点体系
# ============================================================

SUBJECT_KNOWLEDGE_POINTS = {
    "高等数学": """
高等数学知识点体系（参考同济版《高等数学》上下册，供参考，不限于以下内容）：

【第一章 函数与极限】F01函数的概念与性质 F02极限的定义与计算 F03无穷小与无穷大 F04极限存在准则 F05连续与间断 F06闭区间上连续函数的性质
【第二章 导数与微分】D01导数的定义与几何意义 D02基本求导公式 D03四则运算求导法则 D04复合函数求导（链式法则）D05隐函数求导 D06由参数方程确定的函数求导 D07高阶导数 D08微分的概念与运算
【第三章 中值定理与导数的应用】A01罗尔定理 A02拉格朗日中值定理 A03柯西中值定理 A04洛必达法则 A05函数的单调性与极值 A06函数的凹凸性与拐点 A07最值问题 A08曲率与曲率圆
【第四章 不定积分】I01不定积分的概念与性质 I02换元积分法 I03分部积分法 I04有理函数的积分
【第五章 定积分】I05定积分的概念与性质 I06牛顿-莱布尼茨公式 I07定积分的换元法与分部积分法 I08反常积分
【第六章 定积分的应用】I09定积分的几何应用（面积、体积、弧长） I10定积分的物理应用（功、水压力、引力）
【第七章 微分方程】DE01可分离变量的微分方程 DE02齐次方程 DE03一阶线性微分方程 DE04可降阶的高阶方程 DE05二阶常系数线性微分方程
【第八章 空间解析几何与向量代数】G01向量及其线性运算 G02数量积与向量积 G03平面及其方程 G04空间直线及其方程 G05曲面与空间曲线
【第九章 多元函数微分法】M01多元函数的概念与极限 M02偏导数 M03全微分 M04多元复合函数求导 M05隐函数求导公式 M06方向导数与梯度 M07多元函数的极值
【第十章 重积分】M08二重积分的概念与计算 M09三重积分 M10重积分的应用
【第十一章 曲线积分与曲面积分】M11第一类曲线积分 M12第二类曲线积分 M13格林公式 M14第一类曲面积分 M15第二类曲面积分 M16高斯公式
【第十二章 无穷级数】S01常数项级数的概念与性质 S02正项级数审敛法 S03交错级数与莱布尼茨定理 S04幂级数 S05函数展开成幂级数 S06傅里叶级数
""",

    "线性代数": """
线性代数常见知识点分类（供参考，不限于以下内容）：

【行列式】DET01行列式的定义与性质 DET02行列式的计算 DET03克莱姆法则
【矩阵】M01矩阵的运算 M02逆矩阵 M03矩阵的秩 M04初等变换 M05分块矩阵
【线性方程组】LE01齐次线性方程组 LE02非齐次线性方程组 LE03解的结构
【向量与向量空间】V01向量的线性组合 V02线性相关与线性无关 V03向量组的秩 V04基与维数
【特征值与特征向量】EIG01特征值与特征向量 EIG02相似矩阵 EIG03矩阵的对角化 EIG04正交矩阵
【二次型】Q01二次型的概念 Q02化二次型为标准形 Q03正定二次型
""",

    "概率论与数理统计": """
概率论与数理统计常见知识点分类（供参考，不限于以下内容）：

【概率基础】P01随机事件与概率 P02古典概型 P03条件概率 P04全概率公式与贝叶斯公式 P05独立性
【随机变量】RV01离散型随机变量 RV02连续型随机变量 RV03分布函数 RV04常见分布（二项/泊松/均匀/正态/指数）
【数字特征】N01期望 N02方差 N03协方差与相关系数 N04矩
【大数定律与中心极限定理】LLN01大数定律 LLN02中心极限定理
【数理统计】ST01样本与抽样分布 ST02参数估计 ST03假设检验 ST04回归分析
""",

    "离散数学": """
离散数学常见知识点分类（供参考，不限于以下内容）：

【数理逻辑】L01命题逻辑 L02谓词逻辑 L03推理理论 L04自然演绎
【集合论】SET01集合的基本概念 SET02关系 SET03等价关系与偏序关系 SET04函数
【图论】G01图的基本概念 G02路径与连通 G03树 G04欧拉图与哈密顿图 G05平面图
【组合数学】C01基本计数原理 C02排列与组合 C03容斥原理 C04生成函数
【代数结构】AL01半群与群 AL02环与域 AL03格与布尔代数
""",

    "大学物理": """
大学物理常见知识点分类（供参考，不限于以下内容）：

【力学】ME01质点运动学 ME02牛顿运动定律 ME03功与能 ME04动量与冲量 ME05刚体力学
【电磁学】EM01静电场 EM02电势 EM03稳恒电流 EM04磁场 EM05电磁感应 EM06电磁波
【热学】TH01气体动理论 TH02热力学第一定律 TH03热力学第二定律
【光学】OP01几何光学 OP02波动光学 OP03干涉 OP04衍射
【近代物理】MO01狭义相对论 MO02量子力学基础 MO03原子物理
""",

    "其他": """
请根据题目内容自行判断所属学科和知识点领域。
"""
}

ERROR_TYPES = """
常见错误类型（供参考）：
- E01 概念理解错误（对基本概念理解有偏差）
- E02 公式或法则错误（公式记错、法则用错）
- E03 计算错误（运算过程中算错）
- E04 审题错误（没看清题目条件）
- E05 方法选择错误（解题思路不对）
- E06 步骤遗漏（解题过程中跳步或漏步骤）
- E07 其他
"""


# ============================================================
#  构建学科感知的系统 Prompt
# ============================================================

def build_system_prompt(subject: str) -> str:
    kp_ref = SUBJECT_KNOWLEDGE_POINTS.get(subject, SUBJECT_KNOWLEDGE_POINTS["其他"])

    return f"""你是一位经验丰富、循循善诱的{subject}老师，擅长深入分析学生的错题，精准定位知识薄弱点，并给出有深度、可操作的学习建议。

你的任务是：给定一道{subject}题目、学生的作答、以及标准答案，深入分析学生的错误，给出详细的诊断结果。

## 参考知识点体系
{kp_ref}

## 参考错误类型
{ERROR_TYPES}

## 输出要求
请严格按照以下 JSON 格式输出（不要输出其他文字，不要加解释）：

```json
{{
  "subject": "{subject}",
  "primary_knowledge_point": {{
    "id": "知识点编号",
    "name": "知识点名称"
  }},
  "related_knowledge_points": [
    {{"id": "编号", "name": "名称"}}
  ],
  "error_type": {{
    "id": "错误类型编号",
    "name": "错误类型名称"
  }},
  "error_reason": "详细的错误分析，至少150字。要求：1.先指出学生哪里做对了（肯定正确部分）；2.精确说明错误出在哪一步；3.解释为什么这一步是错的，正确的做法应该是什么；4.深入分析这个错误反映了什么知识薄弱点；5.语气鼓励，让学生有信心改进。用换行符分段。",
  "weakness": "学生最薄弱的具体环节，用4-8个字概括",
  "mastery_estimate": 0.0到1.0之间的小数，表示学生对该知识点的掌握程度估计,
  "recommendation": [
    "第1步：具体的学习建议，包含要做什么、怎么做、用什么资源。每条至少30字。",
    "第2步：具体的学习建议",
    "第3步：具体的学习建议",
    "第4步：具体的学习建议"
  ]
}}
```

## 注意事项
1. primary_knowledge_point 是这道题最核心的知识点，只有一个
2. related_knowledge_points 可以有 0-3 个，也可以为空数组 []
3. error_reason 必须详细且有深度，至少150字
4. mastery_estimate 要合理：完全不会给0.2-0.4，部分会给0.4-0.7，粗心给0.7-0.9
5. recommendation 每条必须具体可操作，至少30字
6. 给出4-5步学习路径，从易到难
7. 所有输出用中文
"""


# ============================================================
#  诊断函数
# ============================================================

def diagnose(question: str, student_answer: str, correct_answer: str, subject: str = "高等数学") -> dict:
    """
    诊断一道错题（含 RAG 知识检索增强）。
    """
    system_prompt = build_system_prompt(subject)

    # RAG: 检索相关教材知识
    rag_context = build_rag_context(question, student_answer, subject)

    user_prompt = f"""请分析以下{subject}错题：

【题目】
{question}

【学生答案】
{student_answer}

【标准答案】
{correct_answer}
{rag_context}

请按要求的 JSON 格式输出诊断结果。注意 error_reason 至少150字，recommendation 每条至少30字，要具体可操作。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    result = chat_json(messages, temperature=0.3)
    result = _validate_result(result, subject)
    return result


def diagnose_stream(question: str, student_answer: str, correct_answer: str, subject: str = "高等数学"):
    """
    流式诊断：逐块 yield AI 输出的原始文本。
    前端收到完整 JSON 后解析渲染。

    Yields:
        str: AI 输出的文本片段
    """
    system_prompt = build_system_prompt(subject)

    rag_context = build_rag_context(question, student_answer, subject)

    user_prompt = f"""请分析以下{subject}错题：

【题目】
{question}

【学生答案】
{student_answer}

【标准答案】
{correct_answer}
{rag_context}

请按要求的 JSON 格式输出诊断结果。注意 error_reason 至少150字，recommendation 每条至少30字，要具体可操作。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    yield from chat_stream(messages, temperature=0.3)


def _validate_result(result: dict, subject: str = "高等数学") -> dict:
    """校验并补全诊断结果"""
    result.setdefault("subject", subject)

    if "primary_knowledge_point" not in result or not isinstance(result["primary_knowledge_point"], dict):
        result["primary_knowledge_point"] = {"id": "UNKNOWN", "name": "未知知识点"}
    kp = result["primary_knowledge_point"]
    kp.setdefault("id", "UNKNOWN")
    kp.setdefault("name", "未知知识点")

    if "related_knowledge_points" not in result or not isinstance(result["related_knowledge_points"], list):
        result["related_knowledge_points"] = []

    if "error_type" not in result or not isinstance(result["error_type"], dict):
        result["error_type"] = {"id": "E07", "name": "其他"}
    et = result["error_type"]
    et.setdefault("id", "E07")
    et.setdefault("name", "其他")

    if "error_reason" not in result or not result["error_reason"]:
        result["error_reason"] = "未能准确分析错误原因，建议咨询老师。"

    if "weakness" not in result or not result["weakness"]:
        result["weakness"] = result["primary_knowledge_point"].get("name", "知识点掌握")

    me = result.get("mastery_estimate", 0.5)
    try:
        me = float(me)
        me = max(0.0, min(1.0, me))
    except (ValueError, TypeError):
        me = 0.5
    result["mastery_estimate"] = me

    if "recommendation" not in result or not isinstance(result["recommendation"], list):
        result["recommendation"] = ["复习相关知识点", "完成练习题", "重新测试"]

    return result


# ============================================================
#  练习题生成（学科感知）
# ============================================================

def build_practice_prompt(subject: str) -> str:
    return f"""你是一位{subject}题库专家，擅长根据学生的薄弱点生成针对性的练习题，并提供详细的解题过程。

你的任务是：给定一个薄弱知识点，生成几道选择题，每道题都附带详细的解答过程。

## 输出要求
请严格按照以下 JSON 格式输出：

```json
{{
  "questions": [
    {{
      "question": "题目内容",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "correct": 0,
      "explanation": "详细的解答过程。要求：1.指出正确答案；2.分步骤写出完整解题过程；3.说明每一步用到的公式或法则；4.解释其他选项为什么错误。用换行符分段。"
    }}
  ]
}}
```

## 注意事项
1. 生成 count 道选择题，每题 4 个选项
2. correct 是正确选项的索引（0=A, 1=B, 2=C, 3=D）
3. 题目难度循序渐进
4. explanation 必须详细，至少100字
5. 所有输出用中文
6. 直接输出 JSON，不要加其他文字
"""


def generate_practice_questions(weakness: str, count: int = 3, subject: str = "高等数学") -> list:
    """根据薄弱点生成针对性练习题"""
    system_prompt = build_practice_prompt(subject)

    user_prompt = f"""请根据以下薄弱点生成 {count} 道选择题：

学科：{subject}
薄弱知识点：{weakness}

要求：
1. 第1题简单（基础概念）
2. 第2题中等（基础应用）
3. 第3题稍难（综合应用）
4. 每道题都要有详细的 explanation 解答过程

请按要求的 JSON 格式输出。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    result = chat_json(messages, temperature=0.6)

    questions = result.get("questions", [])

    valid_questions = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if "question" not in q or "options" not in q or "correct" not in q:
            continue
        if not isinstance(q["options"], list) or len(q["options"]) < 2:
            continue
        try:
            q["correct"] = int(q["correct"])
        except (ValueError, TypeError):
            continue
        if q["correct"] < 0 or q["correct"] >= len(q["options"]):
            continue
        if "explanation" not in q or not q["explanation"]:
            correct_letter = chr(65 + q["correct"])
            q["explanation"] = f"正确答案是 {correct_letter}。{q['options'][q['correct']]}。建议复习相关知识点后重新理解这道题。"
        valid_questions.append(q)

    if not valid_questions:
        raise Exception("生成的练习题格式不正确")

    return valid_questions[:count]
