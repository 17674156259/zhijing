"""
题库系统
========
预置练习题，按学科+知识点分类。
练习时优先从题库抽题，不足时 AI 生成补充。
参考同济版《高等数学》上下册知识体系。
"""

import json
import random
from models.database import get_db
from utils.logger import logger

# 预置题库
QUESTION_BANK = [
    # ===== 第一章 函数与极限 =====
    {
        "subject": "高等数学",
        "knowledge_point": "极限",
        "question": "lim(x→0) sin(x)/x = ?",
        "options": ["0", "1", "∞", "不存在"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n这是经典极限：lim(x→0) sin(x)/x = 1。\n可用洛必达法则：lim cos(x)/1 = 1。\n也可用泰勒展开：sin(x) ≈ x - x³/6，所以 sin(x)/x ≈ 1 - x²/6 → 1。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "极限",
        "question": "lim(x→0) (1 + x)^(1/x) = ?",
        "options": ["1", "e", "0", "∞"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n这是第二重要极限：lim(x→0)(1+x)^(1/x) = e。\n令 t = 1/x，当 x→0+ 时 t→∞，即 lim(t→∞)(1+1/t)^t = e。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "极限",
        "question": "lim(x→∞) (1 + 1/x)^x = ?",
        "options": ["1", "e", "0", "∞"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n这是第二重要极限的标准形式：lim(x→∞)(1+1/x)^x = e。\nA 错误，因为底数趋近1但指数趋近∞，属于1^∞型未定式。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "连续与间断",
        "question": "f(x) = {x, x≤1; 2-x, x>1} 在 x=1 处是否连续？",
        "options": ["连续", "跳跃间断", "可去间断", "无穷间断"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nf(1) = 1\nlim(x→1⁻) f(x) = lim x = 1\nlim(x→1⁺) f(x) = lim(2-x) = 1\n左右极限相等且等于函数值，故连续。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "无穷小与无穷大",
        "question": "当 x→0 时，sin(x²) 是 x 的几阶无穷小？",
        "options": ["1阶", "2阶", "3阶", "4阶"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\nlim(x→0) sin(x²)/x^n = 1 当且仅当 n=2。\n因为 sin(x²) ≈ x²（泰勒展开），所以 sin(x²) 是 x 的 2 阶无穷小。"
    },
    # ===== 第二章 导数与微分 =====
    {
        "subject": "高等数学",
        "knowledge_point": "复合函数求导",
        "question": "求 f(x) = sin(3x² + 1) 的导数 f'(x)",
        "options": ["f'(x) = 6x cos(3x² + 1)", "f'(x) = cos(3x² + 1)", "f'(x) = 3x cos(3x² + 1)", "f'(x) = 6x² cos(3x² + 1)"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n1. 外层 sin(u)，内层 u = 3x² + 1\n2. 外层导数：cos(u)\n3. 内层导数：6x\n4. 链式法则：f'(x) = cos(3x² + 1) · 6x = 6x cos(3x² + 1)\n\nB 遗漏内层导数，C 内层求导错误，D 多了x。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "复合函数求导",
        "question": "求 f(x) = e^(2x) 的导数 f'(x)",
        "options": ["f'(x) = e^(2x)", "f'(x) = 2e^(2x)", "f'(x) = x² e^(2x)", "f'(x) = e²"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n1. 外层 e^u，内层 u = 2x\n2. 外层导数：e^u\n3. 内层导数：2\n4. f'(x) = e^(2x) · 2 = 2e^(2x)\n\nA 遗漏内层导数，C 误当幂函数，D 完全错误。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "复合函数求导",
        "question": "求 f(x) = cos(x³) 的导数 f'(x)",
        "options": ["f'(x) = -sin(x³)", "f'(x) = -3x² sin(x³)", "f'(x) = 3x² sin(x³)", "f'(x) = -3x sin(x³)"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n1. 外层 cos(u)，内层 u = x³\n2. 外层导数：-sin(u)\n3. 内层导数：3x²\n4. f'(x) = -sin(x³) · 3x² = -3x² sin(x³)\n\nA 遗漏内层，C 符号错误，D 内层求导错误。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "导数的定义与几何意义",
        "question": "f(x) = x² 在 x=3 处的切线方程是？",
        "options": ["y = 6x - 9", "y = 6x + 9", "y = 3x - 9", "y = 2x - 3"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n1. f(3) = 9\n2. f'(x) = 2x，f'(3) = 6（切线斜率）\n3. 点斜式：y - 9 = 6(x - 3)\n4. 化简：y = 6x - 9\n\nB 截距符号错误，C 斜率错误，D 斜率和截距都错。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "隐函数求导",
        "question": "x² + y² = 25，求 dy/dx",
        "options": ["dy/dx = -x/y", "dy/dx = x/y", "dy/dx = y/x", "dy/dx = -y/x"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n对方程 x² + y² = 25 两边求导（y 是 x 的函数）：\n2x + 2y · dy/dx = 0\ndy/dx = -2x / (2y) = -x/y\n\nB 符号错误，C 分子分母颠倒，D 两者都错。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "高阶导数",
        "question": "f(x) = sin(x)，f⁽⁴⁾(x) = ?",
        "options": ["sin(x)", "-sin(x)", "cos(x)", "-cos(x)"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nf(x) = sin(x)\nf'(x) = cos(x)\nf''(x) = -sin(x)\nf'''(x) = -cos(x)\nf⁽⁴⁾(x) = sin(x)\n\n求导周期为4：sin→cos→-sin→-cos→sin，所以4阶导数回到 sin(x)。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "高阶导数",
        "question": "f(x) = ln(x)，f''(x) = ?",
        "options": ["1/x", "-1/x²", "1/x²", "-1/x"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\nf(x) = ln(x)\nf'(x) = 1/x\nf''(x) = -1/x²\n\nA 是一阶导数，C 符号错误，D 混淆了导数。"
    },
    # ===== 第三章 中值定理与导数的应用 =====
    {
        "subject": "高等数学",
        "knowledge_point": "洛必达法则",
        "question": "lim(x→0) (e^x - 1)/x = ?",
        "options": ["0", "1", "e", "∞"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n0/0 型未定式，用洛必达法则：\nlim (e^x - 1)/x = lim e^x/1 = e^0 = 1\n\n也可用泰勒展开：e^x ≈ 1 + x + x²/2，所以 (e^x-1)/x ≈ 1 + x/2 → 1。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "洛必达法则",
        "question": "lim(x→0) ln(1+x)/x = ?",
        "options": ["0", "1", "e", "∞"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n0/0 型未定式，用洛必达法则：\nlim ln(1+x)/x = lim 1/(1+x) = 1\n\n也可用等价无穷小：ln(1+x) ~ x（x→0时），所以 lim = 1。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "函数的单调性与极值",
        "question": "f(x) = x³ - 3x 的极小值点是？",
        "options": ["x = -1", "x = 0", "x = 1", "x = 3"],
        "correct": 2,
        "explanation": "### 正确答案：C\n\nf'(x) = 3x² - 3 = 3(x²-1) = 0 → x = ±1\nf''(x) = 6x\nf''(-1) = -6 < 0 → x=-1 是极大值点\nf''(1) = 6 > 0 → x=1 是极小值点"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "函数的凹凸性与拐点",
        "question": "f(x) = x³ 的拐点是？",
        "options": ["x = 0", "x = 1", "x = -1", "无拐点"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nf'(x) = 3x²\nf''(x) = 6x\nf''(x) = 0 → x = 0\n当 x < 0 时 f'' < 0（凸），当 x > 0 时 f'' > 0（凹）\nf'' 变号，故 x=0 是拐点。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "罗尔定理",
        "question": "下列哪个函数在 [0,1] 上满足罗尔定理条件？",
        "options": ["f(x)=1/x", "f(x)=x²（f(0)≠f(1)）", "f(x)=|x|", "f(x)=x²（f(0)=f(1)时修改定义域）"],
        "correct": 3,
        "explanation": "### 正确答案：D\n\n罗尔定理要求：1)闭区间连续 2)开区间可导 3)端点值相等。\n1/x 在 x=0 不连续；x² 在[0,1]上 f(0)=0≠f(1)=1；|x| 在 x=0 不可导。\n若取 f(x)=x² 在[-1,1]上则 f(-1)=f(1)=1，满足罗尔定理。"
    },
    # ===== 第四章 不定积分 =====
    {
        "subject": "高等数学",
        "knowledge_point": "换元积分法",
        "question": "∫ 2x e^(x²) dx = ?",
        "options": ["e^(x²) + C", "x² e^(x²) + C", "2e^(x²) + C", "(1/2)e^(x²) + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n令 u = x²，则 du = 2x dx\n∫ 2x e^(x²) dx = ∫ e^u du = e^u + C = e^(x²) + C\n\nB 误乘 x²，C 多乘 2，D 误除 2。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "换元积分法",
        "question": "∫ cos(2x) dx = ?",
        "options": ["sin(2x) + C", "(1/2)sin(2x) + C", "2sin(2x) + C", "-sin(2x) + C"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n令 u = 2x，du = 2dx，dx = du/2\n∫ cos(2x)dx = ∫ cos(u)·(du/2) = (1/2)sin(u) + C = (1/2)sin(2x) + C\n\nA 遗漏系数 1/2，C 多乘 2，D 符号错误。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "换元积分法",
        "question": "∫ 1/(1+x²) dx = ?",
        "options": ["arctan(x) + C", "arcsin(x) + C", "ln(1+x²) + C", "tan(x) + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n这是基本积分公式：∫ 1/(1+x²) dx = arctan(x) + C\n\nB 是 ∫1/√(1-x²)dx 的结果，C 遗漏了系数和分子，D 完全错误。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "分部积分法",
        "question": "∫ x e^x dx = ?",
        "options": ["xe^x + C", "xe^x - e^x + C", "e^x(x-1) + C", "B和C都正确"],
        "correct": 3,
        "explanation": "### 正确答案：D\n\n分部积分：u=x, dv=e^x dx → du=dx, v=e^x\n∫ x e^x dx = xe^x - ∫ e^x dx = xe^x - e^x + C = e^x(x-1) + C\nB和C是等价表达式。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "分部积分法",
        "question": "∫ x ln(x) dx = ?",
        "options": ["(x²/2)ln(x) - x²/4 + C", "(x²/2)ln(x) + x²/4 + C", "x² ln(x) - x²/2 + C", "(1/2)x² ln(x) + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n分部积分：u=ln(x), dv=x dx → du=(1/x)dx, v=x²/2\n∫ x ln(x) dx = (x²/2)ln(x) - ∫(x²/2)·(1/x)dx\n= (x²/2)ln(x) - ∫(x/2)dx = (x²/2)ln(x) - x²/4 + C"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "基本积分公式",
        "question": "∫ sec²(x) dx = ?",
        "options": ["tan(x) + C", "-cot(x) + C", "sec(x)tan(x) + C", "-csc(x)cot(x) + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n这是基本积分公式：∫ sec²(x) dx = tan(x) + C\n因为 d/dx[tan(x)] = sec²(x)。\n\nB 是 ∫csc²(x)dx 的结果，C 是 ∫sec(x)tan(x)dx 的结果。"
    },
    # ===== 第五章 定积分 =====
    {
        "subject": "高等数学",
        "knowledge_point": "牛顿-莱布尼茨公式",
        "question": "∫₀¹ x² dx = ?",
        "options": ["1/3", "1/2", "1", "2/3"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n原函数 F(x) = x³/3\n∫₀¹ x² dx = F(1) - F(0) = 1/3 - 0 = 1/3"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "牛顿-莱布尼茨公式",
        "question": "∫₀^(π/2) sin(x) dx = ?",
        "options": ["0", "1", "-1", "π/2"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n原函数 F(x) = -cos(x)\n∫₀^(π/2) sin(x) dx = [-cos(π/2)] - [-cos(0)] = 0 - (-1) = 1"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "定积分的概念与性质",
        "question": "∫ₐᵃ f(x) dx = ?",
        "options": ["f(a)", "0", "1", "f(a)·a"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n定积分的上下限相等时，积分区间长度为0，积分值为0。这是定积分的基本性质。"
    },
    # ===== 第六章 定积分的应用 =====
    {
        "subject": "高等数学",
        "knowledge_point": "定积分的几何应用",
        "question": "曲线 y = x² 与 y = x 围成的面积是？",
        "options": ["1/6", "1/3", "1/2", "1"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n交点：x² = x → x=0 或 x=1\n面积 = ∫₀¹ (x - x²) dx = [x²/2 - x³/3]₀¹ = 1/2 - 1/3 = 1/6"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "定积分的几何应用",
        "question": "y = √x (0≤x≤1) 绕 x 轴旋转的旋转体体积是？",
        "options": ["π/2", "π/3", "π/4", "2π/3"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nV = π ∫₀¹ (√x)² dx = π ∫₀¹ x dx = π[x²/2]₀¹ = π/2"
    },
    # ===== 第七章 微分方程 =====
    {
        "subject": "高等数学",
        "knowledge_point": "可分离变量的微分方程",
        "question": "dy/dx = y 的通解是？",
        "options": ["y = Ce^x", "y = Cx", "y = e^x + C", "y = ln(x) + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n分离变量：dy/y = dx\n积分：ln|y| = x + C₁\n通解：y = Ce^x（其中 C = ±e^C₁）"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "可分离变量的微分方程",
        "question": "dy/dx = xy 的通解是？",
        "options": ["y = Ce^(x²/2)", "y = Cx e^x", "y = Ce^x", "y = Cx²"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n分离变量：dy/y = x dx\n积分：ln|y| = x²/2 + C₁\n通解：y = Ce^(x²/2)"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "一阶线性微分方程",
        "question": "dy/dx + y = e^x 的通解是？（积分因子法）",
        "options": ["y = (1/2)e^x + Ce^(-x)", "y = e^x + Ce^(-x)", "y = (1/2)e^x + C", "y = e^x + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nP(x)=1, 积分因子 μ = e^(∫1dx) = e^x\nd/dx(y·e^x) = e^(2x)\ny·e^x = (1/2)e^(2x) + C\ny = (1/2)e^x + Ce^(-x)"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "二阶常系数线性微分方程",
        "question": "y'' + 4y = 0 的通解是？",
        "options": ["y = C₁cos(2x) + C₂sin(2x)", "y = C₁e^(2x) + C₂e^(-2x)", "y = (C₁+C₂x)e^(2x)", "y = C₁ + C₂x"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n特征方程：r² + 4 = 0 → r = ±2i（共轭复根）\n通解：y = C₁cos(2x) + C₂sin(2x)\n\nB 是 r=±2 实根的情况，C 是重根的情况，D 是 r=0 的情况。"
    },
    # ===== 第八章 空间解析几何 =====
    {
        "subject": "高等数学",
        "knowledge_point": "向量及其线性运算",
        "question": "a = (1,2,3), b = (4,5,6)，a·b = ?",
        "options": ["32", "(4,10,18)", "28", "6"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n点积：a·b = 1×4 + 2×5 + 3×6 = 4 + 10 + 18 = 32\n\nB 是分量积（不是标准运算），C 计算错误，D 等于 b-a 的某个分量。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "数量积与向量积",
        "question": "a = (1,0,0), b = (0,1,0)，a×b = ?",
        "options": ["(0,0,1)", "(0,0,-1)", "(1,1,0)", "0"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n向量积公式：\na×b = |i  j  k; 1 0 0; 0 1 0|\n= i(0×0-0×1) - j(1×0-0×0) + k(1×1-0×0)\n= (0, 0, 1)\n\n由右手定则，x轴×y轴=z轴。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "平面及其方程",
        "question": "过点 (1,2,3) 且法向量为 n=(1,1,1) 的平面方程是？",
        "options": ["x+y+z=6", "x+y+z=0", "x+y+z=3", "x-y+z=2"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n点法式方程：A(x-x₀)+B(y-y₀)+C(z-z₀)=0\n代入得：1(x-1)+1(y-2)+1(z-3)=0\n化简：x+y+z=6\n\nB 法向量错误，C 截距错误，D 法向量与题意不符。"
    },
    # ===== 第九章 多元函数微分法 =====
    {
        "subject": "高等数学",
        "knowledge_point": "偏导数",
        "question": "f(x,y) = x²y³，∂f/∂x = ?",
        "options": ["2xy³", "x²·3y²", "2x + 3y", "x²y³"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n对 x 求偏导，把 y 当常数：\n∂f/∂x = 2x · y³ = 2xy³\n\nB 是 ∂f/∂y，C 错误地分离了变量，D 是原函数。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "偏导数",
        "question": "f(x,y) = x²y³，∂²f/∂x∂y = ?",
        "options": ["6xy²", "2x·3y²", "6x²y", "2xy²"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n先对 x 求偏导：∂f/∂x = 2xy³\n再对 y 求偏导：∂²f/∂x∂y = 2x·3y² = 6xy²\n\nB 未化简，C 混淆了求导顺序的变量，D 求导不完整。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "全微分",
        "question": "z = x² + y²，dz = ?",
        "options": ["2x dx + 2y dy", "2x + 2y", "x²dx + y²dy", "2(x+y)"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n全微分公式：dz = (∂z/∂x)dx + (∂z/∂y)dy\n∂z/∂x = 2x，∂z/∂y = 2y\ndz = 2x dx + 2y dy"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "多元函数的极值",
        "question": "f(x,y) = x² + y² 的极小值是？",
        "options": ["0（在(0,0)处）", "1（在(1,1)处）", "2（在(1,1)处）", "无极值"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n∂f/∂x = 2x = 0 → x=0\n∂f/∂y = 2y = 0 → y=0\n驻点(0,0)，f(0,0)=0\n二阶判别：AC-B² = 2×2-0 = 4 > 0 且 A=2>0\n故(0,0)是极小值点，极小值为0。"
    },
    # ===== 第十章 重积分 =====
    {
        "subject": "高等数学",
        "knowledge_point": "二重积分",
        "question": "∫∫_D 1 dσ，D = {(x,y): 0≤x≤1, 0≤y≤1}，积分值是？",
        "options": ["1", "2", "4", "1/2"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n∫∫_D 1 dσ 表示区域 D 的面积。\nD 是边长为1的正方形，面积 = 1×1 = 1。\n也可计算：∫₀¹∫₀¹ 1 dxdy = ∫₀¹ 1 dy = 1"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "二重积分",
        "question": "∫₀¹∫₀ˣ dy dx 的值是？（先对y积分）",
        "options": ["1/2", "1", "1/3", "1/4"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n∫₀¹∫₀ˣ dy dx = ∫₀¹ [y]₀ˣ dx = ∫₀¹ x dx = x²/2 |₀¹ = 1/2\n\n这个积分表示三角形区域{0≤y≤x, 0≤x≤1}的面积。"
    },
    # ===== 第十一章 曲线积分与曲面积分 =====
    {
        "subject": "高等数学",
        "knowledge_point": "格林公式",
        "question": "格林公式 ∮_L Pdx + Qdy = ?",
        "options": ["∫∫_D (∂Q/∂x - ∂P/∂y) dσ", "∫∫_D (∂P/∂x + ∂Q/∂y) dσ", "∫∫_D (P+Q) dσ", "∮_L (P+Q) ds"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n格林公式将曲线积分转化为二重积分：\n∮_L Pdx + Qdy = ∫∫_D (∂Q/∂x - ∂P/∂y) dσ\n其中 L 是区域 D 的正向边界曲线。\n\nB 符号错误，C 和 D 完全错误。"
    },
    # ===== 第十二章 无穷级数 =====
    {
        "subject": "高等数学",
        "knowledge_point": "常数项级数",
        "question": "级数 Σ(n=1→∞) 1/n² 的和是？",
        "options": ["π²/6", "1", "∞", "π/6"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n这是著名的 Basel 问题，欧拉证明了：\nΣ(n=1→∞) 1/n² = π²/6 ≈ 1.6449\n\nB 过小，C 错误（p=2>1 收敛），D 错误。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "正项级数审敛法",
        "question": "级数 Σ(n=1→∞) 1/n 的敛散性是？",
        "options": ["发散", "收敛", "条件收敛", "无法判断"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n这是调和级数，是 p 级数中 p=1 的情况。\np 级数 Σ1/n^p 当 p>1 时收敛，p≤1 时发散。\n调和级数发散，尽管通项趋近于0。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "幂级数",
        "question": "幂级数 Σ(n=0→∞) x^n 的收敛半径是？",
        "options": ["R=1", "R=∞", "R=0", "R=2"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n这是等比级数，公比为 x。\n当 |x| < 1 时收敛，和为 1/(1-x)。\n当 |x| ≥ 1 时发散。\n所以收敛半径 R = 1。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "函数展开成幂级数",
        "question": "e^x 的麦克劳林展开式是？",
        "options": ["Σ(n=0→∞) x^n/n!", "Σ(n=0→∞) x^n", "Σ(n=1→∞) x^n/n", "1 + x + x²"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\ne^x = Σ(n=0→∞) x^n/n! = 1 + x + x²/2! + x³/3! + ...\n收敛域为 (-∞, +∞)。\n\nB 是 1/(1-x) 的展开式，C 缺少常数项，D 不完整。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "交错级数",
        "question": "级数 Σ(n=1→∞) (-1)^n / n 的敛散性是？",
        "options": ["条件收敛", "绝对收敛", "发散", "无法判断"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n这是交错级数（莱布尼茨级数）。\n1. 通项 |aₙ| = 1/n 单调递减\n2. lim 1/n = 0\n满足莱布尼茨定理条件，级数收敛。\n但 Σ|(-1)^n/n| = Σ1/n（调和级数）发散。\n故为条件收敛。"
    },
    # ===== 线性代数 =====
    {
        "subject": "线性代数",
        "knowledge_point": "矩阵的秩",
        "question": "若 3×3 矩阵 A 的行列式 |A| = 0，则 rank(A) 的可能值是？",
        "options": ["0", "1或2", "3", "0或1或2"],
        "correct": 3,
        "explanation": "### 正确答案：D\n\n|A|=0 说明 A 不满秩，即 rank(A) < 3。但具体秩可能是 0（零矩阵）、1 或 2，取决于矩阵的具体情况。"
    },
    {
        "subject": "线性代数",
        "knowledge_point": "特征值与特征向量",
        "question": "若 λ 是矩阵 A 的特征值，则 A² 的特征值是？",
        "options": ["λ", "λ²", "2λ", "√λ"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n若 Ax = λx，则 A²x = A(Ax) = A(λx) = λ(Ax) = λ²x。\n所以 A² 的特征值是 λ²。"
    },
    {
        "subject": "线性代数",
        "knowledge_point": "线性方程组",
        "question": "n元齐次线性方程组 Ax=0 有非零解的充要条件是？",
        "options": ["|A| ≠ 0", "|A| = 0", "A 是方阵", "方程个数 < n"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n齐次方程组有非零解 ⟺ 系数矩阵的行列式为零 ⟺ rank(A) < n。|A|≠0 时只有零解。"
    },
    # ===== 概率论 =====
    {
        "subject": "概率论与数理统计",
        "knowledge_point": "贝叶斯公式",
        "question": "P(A)=0.3, P(B|A)=0.8, P(B|¬A)=0.2，求 P(A|B)？",
        "options": ["0.3", "0.54", "0.63", "0.8"],
        "correct": 2,
        "explanation": "### 正确答案：C\n\nP(B) = P(B|A)P(A) + P(B|¬A)P(¬A) = 0.8×0.3 + 0.2×0.7 = 0.24+0.14 = 0.38\nP(A|B) = P(B|A)P(A)/P(B) = 0.24/0.38 ≈ 0.63"
    },
    {
        "subject": "概率论与数理统计",
        "knowledge_point": "期望与方差",
        "question": "X~N(μ, σ²)，则 E(X²) = ?",
        "options": ["μ²", "σ²", "μ² + σ²", "μ + σ²"],
        "correct": 2,
        "explanation": "### 正确答案：C\n\nD(X) = E(X²) - [E(X)]² = E(X²) - μ²\n所以 E(X²) = D(X) + μ² = σ² + μ²"
    },
    {
        "subject": "概率论与数理统计",
        "knowledge_point": "中心极限定理",
        "question": "设 X₁,...,X₅₀ 独立同分布，E(Xᵢ)=μ, D(Xᵢ)=σ²，则 X̄ 近似服从？",
        "options": ["N(μ, σ²)", "N(μ, σ²/50)", "N(50μ, σ²)", "N(μ, 50σ²)"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n由中心极限定理，X̄ ≈ N(μ, σ²/n)，n=50。\nE(X̄) = μ, D(X̄) = σ²/n = σ²/50。"
    },

    # ===== 补充：图谱空缺节点题目 =====
    # F01 函数的概念与性质
    {
        "subject": "高等数学",
        "knowledge_point": "函数的概念与性质",
        "question": "函数 f(x) = √(x-1) + ln(5-x) 的定义域是？",
        "options": ["[1, 5]", "[1, 5)", "(1, 5)", "(1, 5]"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n需要同时满足两个条件：\n1) 根号内非负：x-1≥0 → x≥1\n2) 对数真数为正：5-x>0 → x<5\n所以定义域为 [1, 5)，左闭右开。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "函数的概念与性质",
        "question": "设 f(x) 是奇函数且在 x=0 处有定义，则 f(0) = ?",
        "options": ["1", "0", "-1", "无法确定"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n奇函数定义：f(-x) = -f(x)。\n令 x=0：f(0) = -f(0) → 2f(0)=0 → f(0)=0。\n奇函数若在原点有定义，则必过原点。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "函数的概念与性质",
        "question": "函数 y = sin(x) + cos(x) 的最小正周期是？",
        "options": ["π", "2π", "π/2", "4π"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\nsin(x) 周期 2π，cos(x) 周期 2π。\ny = sin(x)+cos(x) = √2·sin(x+π/4)，周期仍为 2π。\n两个同周期函数的和的周期是它们周期的最小公倍数。"
    },
    # D02 基本求导公式
    {
        "subject": "高等数学",
        "knowledge_point": "基本求导公式",
        "question": "函数 f(x) = x³ - 2x² + 5x - 3 的导数 f'(x) = ?",
        "options": ["3x² - 4x + 5", "3x² - 2x + 5", "x² - 4x + 5", "3x² - 4x - 3"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n逐项求导：\n- (x³)' = 3x²\n- (-2x²)' = -4x\n- (5x)' = 5\n- (-3)' = 0\n所以 f'(x) = 3x² - 4x + 5。常数项导数为零。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "基本求导公式",
        "question": "函数 f(x) = e^x · ln(x) 的导数 f'(x) = ?",
        "options": ["e^x/x", "e^x·ln(x) + e^x/x", "e^x/x + ln(x)", "e^x·ln(x) - e^x/x"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n使用乘法法则 (uv)' = u'v + uv'：\n- u = e^x, u' = e^x\n- v = ln(x), v' = 1/x\nf'(x) = e^x·ln(x) + e^x·(1/x) = e^x·ln(x) + e^x/x"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "基本求导公式",
        "question": "f(x) = (tan x)' = ?",
        "options": ["sec²x", "1/cos²x", "sec²x", "选项A和C都正确"],
        "correct": 3,
        "explanation": "### 正确答案：D\n\n(tan x)' = (sin x/cos x)' = (cos²x + sin²x)/cos²x = 1/cos²x = sec²x。\nsec x = 1/cos x，所以 sec²x = 1/cos²x。A和C是同一个答案。"
    },
    # D06 微分及其应用
    {
        "subject": "高等数学",
        "knowledge_point": "微分及其应用",
        "question": "函数 y = x² 在 x=3 处的微分 dy = ?",
        "options": ["6dx", "6", "9dx", "6+dx"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\ndy = f'(x)dx。f'(x) = 2x，f'(3) = 6。\n所以 dy = 6dx。微分等于导数乘以自变量的微分 dx。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "微分及其应用",
        "question": "用微分近似计算 √(1.02) ≈ ?",
        "options": ["1.01", "1.02", "1.00", "1.015"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n设 f(x) = √x，f'(x) = 1/(2√x)。\n取 x₀=1, Δx=0.02。\nf(1.02) ≈ f(1) + f'(1)·Δx = 1 + (1/2)×0.02 = 1.01。\n微分近似：Δy ≈ dy = f'(x₀)·Δx。"
    },
    # M03 泰勒公式
    {
        "subject": "高等数学",
        "knowledge_point": "泰勒公式",
        "question": "函数 e^x 在 x=0 处的3阶麦克劳林展开式为？",
        "options": ["1 + x + x²/2 + x³/6", "1 + x + x²/2", "1 + x + x² + x³", "1 + x + x²/2 + x³/3"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\ne^x 的麦克劳林展开：e^x = Σ x^n/n!\n3阶展开：1 + x + x²/2! + x³/3! = 1 + x + x²/2 + x³/6。\n余项为 R₃ = e^ξ·x⁴/24 (ξ在0与x之间)。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "泰勒公式",
        "question": "sin x 的5阶麦克劳林展开式为？",
        "options": ["x - x³/6 + x⁵/120", "x - x³/3 + x⁵/5", "x - x³/2 + x⁵/24", "x - x³/6"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nsin x = x - x³/3! + x⁵/5! - ... = x - x³/6 + x⁵/120 - ...\nsin的展开只含奇次项，系数为 (-1)^n/(2n+1)!。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "泰勒公式",
        "question": "用泰勒公式求 lim(x→0) (e^x - 1 - x) / x² = ?",
        "options": ["1/2", "0", "1", "∞"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\ne^x = 1 + x + x²/2 + o(x²)\ne^x - 1 - x = x²/2 + o(x²)\nlim (x²/2 + o(x²))/x² = 1/2。\n泰勒展开求极限时，展开到分子分母同阶即可。"
    },
    # I04 有理函数积分
    {
        "subject": "高等数学",
        "knowledge_point": "有理函数积分",
        "question": "∫ 1/((x-1)(x+2)) dx = ?",
        "options": ["(1/3)ln|(x-1)/(x+2)| + C", "ln|(x-1)(x+2)| + C", "(1/3)ln|(x+2)/(x-1)| + C", "ln|x-1| + ln|x+2| + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n部分分式分解：1/((x-1)(x+2)) = A/(x-1) + B/(x+2)\n解得 A=1/3, B=-1/3。\n积分 = (1/3)ln|x-1| - (1/3)ln|x+2| + C = (1/3)ln|(x-1)/(x+2)| + C。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "有理函数积分",
        "question": "∫ x/(x²+1) dx = ?",
        "options": ["(1/2)ln(x²+1) + C", "arctan(x) + C", "ln(x²+1) + C", "(1/2)arctan(x) + C"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n凑微分：x dx = (1/2)d(x²+1)。\n∫ x/(x²+1) dx = (1/2)∫ d(x²+1)/(x²+1) = (1/2)ln(x²+1) + C。\n注意：如果分子是1而不是x，则结果是arctan(x)。"
    },
    # DI04 反常积分
    {
        "subject": "高等数学",
        "knowledge_point": "反常积分",
        "question": "∫₁^∞ 1/x² dx = ?",
        "options": ["1", "∞", "0", "2"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n∫₁^∞ 1/x² dx = lim(b→∞) [-1/x]₁^b = lim(b→∞) (-1/b + 1) = 1。\np-积分：∫₁^∞ 1/x^p dx 当 p>1 时收敛。这里 p=2>1，收敛。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "反常积分",
        "question": "∫₀¹ 1/√x dx = ?",
        "options": ["2", "1", "∞", "1/2"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nx=0 是被积函数的瑕点。\n∫₀¹ 1/√x dx = lim(a→0⁺) [2√x]_a^1 = 2 - 0 = 2。\n无界函数反常积分：∫₀¹ 1/x^p dx 当 p<1 时收敛。这里 p=1/2<1，收敛。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "反常积分",
        "question": "下列反常积分中发散的是？",
        "options": ["∫₁^∞ 1/x³ dx", "∫₁^∞ 1/√x dx", "∫₁^∞ 1/x² dx", "∫₀¹ 1/√x dx"],
        "correct": 1,
        "explanation": "### 正确答案：B\n\n无穷限反常积分 ∫₁^∞ 1/x^p dx：p>1收敛，p≤1发散。\nA: p=3>1 收敛；B: p=1/2<1 发散；C: p=2>1 收敛。\nD: 无界函数积分 ∫₀¹ 1/x^p dx，p<1收敛，p=1/2<1 收敛。"
    },
    # D09 多元复合函数求导
    {
        "subject": "高等数学",
        "knowledge_point": "多元复合函数求导",
        "question": "设 z = f(u,v), u = x²+y, v = xy，则 ∂z/∂x = ?",
        "options": ["f₁·2x + f₂·y", "f₁·2x + f₂·x", "f₁·2x", "f₁·x + f₂·y"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n链式法则（树图法）：z→u→x 和 z→v→x 两条路径。\n∂z/∂x = ∂f/∂u·∂u/∂x + ∂f/∂v·∂v/∂x\n= f₁·2x + f₂·y\n其中 f₁ 表示 f 对第一个变量 u 的偏导，f₂ 表示对第二个变量 v 的偏导。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "多元复合函数求导",
        "question": "设 z = f(x²+y²), 则 ∂z/∂y = ?",
        "options": ["f'·2y", "f'·y", "f'·(x²+y²)", "2y"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\nz = f(u), u = x²+y²，只有一个中间变量。\n∂z/∂y = f'(u)·∂u/∂y = f'·2y。\n注意 f 是一元函数（只有一个变量），所以用 f' 而非偏导符号。"
    },
    # DI08 三重积分
    {
        "subject": "高等数学",
        "knowledge_point": "三重积分",
        "question": "在球坐标下，体积元素 dV = ?",
        "options": ["r² sinφ dr dφ dθ", "r sinφ dr dφ dθ", "r² dr dφ dθ", "ρ² sinφ dr dφ dθ"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n球坐标变换：x=r sinφ cosθ, y=r sinφ sinθ, z=r cosφ。\nJacobi行列式 |J| = r² sinφ。\n所以 dV = r² sinφ dr dφ dθ。\n这个公式必须记住，考试中经常用到。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "三重积分",
        "question": "三重积分 ∫∫∫_Ω dV 的几何意义是？",
        "options": ["区域Ω的体积", "区域Ω的面积", "曲面的面积", "曲线的弧长"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n被积函数为1时，三重积分表示空间区域Ω的体积。\n类比：二重积分 ∫∫_D dA 表示平面区域面积，定积分 ∫_a^b dx 表示区间长度。"
    },
    # DI10 曲面积分
    {
        "subject": "高等数学",
        "knowledge_point": "曲面积分",
        "question": "高斯公式 ∯_S P dy dz + Q dz dx + R dx dy = ?",
        "options": ["∫∫∫_Ω (∂P/∂x+∂Q/∂y+∂R/∂z) dV", "∫∫_S (∂Q/∂x-∂P/∂y) dA", "∮_L P dx + Q dy", "∫∫∫_Ω dV"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n高斯公式（散度定理）：闭曲面S外侧的曲面积分 = 区域Ω上的三重积分。\n右端是散度 div F = ∂P/∂x+∂Q/∂y+∂R/∂z 的三重积分。\n条件：S是封闭曲面取外侧，P,Q,R在Ω上有连续一阶偏导。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "曲面积分",
        "question": "斯托克斯公式将曲线积分转化为？",
        "options": ["曲面积分", "二重积分", "三重积分", "定积分"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n斯托克斯公式：空间闭曲线L上的曲线积分 = 以L为边界的曲面S上的曲面积分。\n∮_L P dx + Q dy + R dz = ∫∫_S (curl F)·n dS。\n它建立了曲线积分和曲面积分之间的桥梁，高斯公式则建立曲面积分和三重积分的桥梁。"
    },
    # DI13 傅里叶级数
    {
        "subject": "高等数学",
        "knowledge_point": "傅里叶级数",
        "question": "周期为2π的函数 f(x) 的傅里叶系数 a₀ 的公式是？",
        "options": ["(1/π)∫₋π^π f(x) dx", "(1/2π)∫₋π^π f(x) dx", "(1/π)∫₀^π f(x) dx", "(1/2π)∫₀^{2π} f(x) dx"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n傅里叶系数公式：\na₀ = (1/π)∫₋π^π f(x) dx\naₙ = (1/π)∫₋π^π f(x) cos(nx) dx\nbₙ = (1/π)∫₋π^π f(x) sin(nx) dx\n注意 a₀ 的分母是π不是2π，常数项是 a₀/2。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "傅里叶级数",
        "question": "奇函数的傅里叶级数只含什么项？",
        "options": ["正弦项", "余弦项", "常数项", "正弦和余弦项"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n奇函数 f(-x) = -f(x)。\na₀ = (1/π)∫₋π^π f(x)dx = 0（奇函数在对称区间积分为零）\naₙ = 0（f(x)cos(nx)是奇函数×偶函数=奇函数，积分为零）\nbₙ ≠ 0（f(x)sin(nx)是奇函数×奇函数=偶函数）\n所以奇函数的傅里叶级数只含正弦项（bₙ），称为正弦级数。"
    },
    {
        "subject": "高等数学",
        "knowledge_point": "傅里叶级数",
        "question": "狄利克雷收敛定理保证傅里叶级数在连续点收敛到什么值？",
        "options": ["f(x)", "(f(x+)+f(x-))/2", "0", "f(0)"],
        "correct": 0,
        "explanation": "### 正确答案：A\n\n狄利克雷定理：若 f(x) 满足狄利克雷条件，则其傅里叶级数在\n- 连续点收敛到 f(x)\n- 间断点收敛到 (f(x+)+f(x-))/2（左右极限的平均值）\n题目问的是连续点，所以收敛到 f(x)。"
    },
]


def init_question_bank():
    """将预置题目写入数据库"""
    db = get_db()
    db.execute("DELETE FROM question_bank WHERE is_preset = 1")

    for q in QUESTION_BANK:
        db.execute("""
            INSERT INTO question_bank (subject, knowledge_point, question, options, correct, explanation, is_preset)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            q["subject"], q["knowledge_point"], q["question"],
            json.dumps(q["options"], ensure_ascii=False),
            q["correct"],
            q.get("explanation", ""),
        ))

    db.commit()
    db.close()
    logger.info(f"题库初始化: {len(QUESTION_BANK)} 道预置题目")


def get_questions_from_bank(subject: str, knowledge_point: str = None, count: int = 3) -> list:
    """
    从题库抽题。优先匹配知识点，不足时用同学科补充。
    """
    db = get_db()

    if knowledge_point:
        rows = db.execute(
            "SELECT * FROM question_bank WHERE subject=? AND knowledge_point=? ORDER BY RANDOM() LIMIT ?",
            (subject, knowledge_point, count)
        ).fetchall()

        if len(rows) < count:
            existing_ids = ",".join(str(r["id"]) for r in rows) if rows else "0"
            extra = db.execute(
                f"SELECT * FROM question_bank WHERE subject=? AND id NOT IN ({existing_ids}) ORDER BY RANDOM() LIMIT ?",
                (subject, count - len(rows))
            ).fetchall()
            rows = list(rows) + list(extra)
    else:
        rows = db.execute(
            "SELECT * FROM question_bank WHERE subject=? ORDER BY RANDOM() LIMIT ?",
            (subject, count)
        ).fetchall()

    db.close()

    questions = []
    for row in rows:
        questions.append({
            "question": row["question"],
            "options": json.loads(row["options"]),
            "correct": row["correct"],
            "explanation": row["explanation"],
            "source": "题库"
        })

    logger.info(f"题库抽题: subject={subject}, kp={knowledge_point}, 抽到{len(questions)}道")
    return questions


# ============================================================
# 图谱节点ID → 题库知识点名称映射
# ============================================================
KP_ID_TO_BANK = {
    "F01": ["函数的概念与性质"],
    "F02": ["极限"],
    "F03": ["无穷小与无穷大"],
    "F04": ["连续与间断"],
    "D01": ["导数的定义与几何意义"],
    "D02": ["基本求导公式"],
    "D03": ["复合函数求导"],
    "D04": ["隐函数求导"],
    "D05": ["高阶导数"],
    "D06": ["微分及其应用"],
    "M01": ["罗尔定理"],
    "M02": ["洛必达法则"],
    "M03": ["泰勒公式"],
    "M04": ["函数的单调性与极值"],
    "M05": ["函数的凹凸性与拐点"],
    "I01": ["基本积分公式"],
    "I02": ["换元积分法"],
    "I03": ["分部积分法"],
    "I04": ["有理函数积分"],
    "DI01": ["定积分的概念与性质"],
    "DI02": ["牛顿-莱布尼茨公式"],
    "DI03": ["牛顿-莱布尼茨公式", "定积分的概念与性质"],
    "DI04": ["反常积分"],
    "DI05": ["定积分的几何应用"],
    "DI06": ["定积分的几何应用"],
    "D07": ["偏导数"],
    "D08": ["全微分"],
    "D09": ["多元复合函数求导"],
    "D10": ["隐函数求导"],
    "DI07": ["二重积分"],
    "DI08": ["三重积分"],
    "DI09": ["格林公式"],
    "DI10": ["曲面积分"],
    "DI11": ["常数项级数", "正项级数审敛法", "交错级数"],
    "DI12": ["幂级数", "函数展开成幂级数"],
    "DI13": ["傅里叶级数"],
    "DI14": ["可分离变量的微分方程", "一阶线性微分方程"],
    "DI15": ["二阶常系数线性微分方程"],
}


def get_questions_by_kp_id(kp_id: str, count: int = 3) -> list:
    """根据图谱节点ID从题库抽题，支持一个节点对应多个题库知识点"""
    bank_kps = KP_ID_TO_BANK.get(kp_id, [])
    if not bank_kps:
        return []

    db = get_db()
    placeholders = ",".join("?" * len(bank_kps))
    rows = db.execute(
        f"SELECT * FROM question_bank WHERE subject='高等数学' AND knowledge_point IN ({placeholders}) ORDER BY RANDOM() LIMIT ?",
        (*bank_kps, count)
    ).fetchall()

    questions = []
    for row in rows:
        questions.append({
            "question": row["question"],
            "options": json.loads(row["options"]),
            "correct": row["correct"],
            "explanation": row["explanation"],
            "source": "题库"
        })

    db.close()
    logger.info(f"图谱抽题: kp_id={kp_id}, bank_kps={bank_kps}, 抽到{len(questions)}道")
    return questions
