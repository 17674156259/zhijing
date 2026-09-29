# 知径 · 高数错题诊断与学习路径推荐系统

> 把一道错题，变成下一步学习路径。

一款基于大模型的高等数学错题诊断与学习路径推荐系统，结合 AI 诊断、RAG 检索增强、贝叶斯知识追踪（BKT）和知识图谱，为学生提供精准的错题分析和个性化学习建议。

---

## ✨ 功能特性

### 核心功能
- **AI 错题诊断**：DeepSeek 大模型深度分析，精准定位错误位置，判断错误类型，生成学习路径
- **OCR 图片识别**：豆包视觉模型识别数学公式，自动转换 LaTeX，支持框选裁剪
- **针对性练习**：题库抽题 / AI 生成 / 智能推荐三种模式，难度循序渐进
- **贝叶斯知识追踪**：四参数 BKT 模型动态追踪各知识点掌握度
- **知识图谱**：35 个知识点可视化，智能学习路径，一键发起练习
- **AI 追问对话**：就诊断结果深入提问，支持 Markdown 和数学公式渲染
- **错题本**：收藏 / 备注 / 筛选 / PDF 导出
- **学习看板**：掌握度趋势、薄弱点分布、智能学习建议
- **教师端**：班级管理、学情分析、共性薄弱点统计

### 技术亮点
- RAG 检索增强（关键词倒排索引 + TF-IDF 双层打分）
- LaTeX 反斜杠状态机解析算法（解决 JSON 转义破坏公式问题）
- SSE 流式输出（打字机式实时反馈）
- JWT 认证 + IP 限流 + 内存缓存
- 零框架前端，轻量快速

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | HTML + CSS + JavaScript（零框架） |
| 后端 | Python 3 + Flask 3.0 |
| 数据库 | SQLite |
| AI 模型 | DeepSeek（文本）+ 火山方舟豆包（视觉OCR） |
| 数学渲染 | KaTeX |
| 可视化 | ECharts（知识图谱 + 看板图表） |
| 认证 | JWT（HMAC-SHA256） |

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- DeepSeek API Key
- 火山方舟（豆包视觉模型）API Key（可选，用于 OCR 功能）

### 安装与运行

```bash
# 1. 克隆仓库
git clone <你的仓库地址>
cd zhijing/diagnosis-app

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 4. 启动服务
python app.py
```

启动后访问：http://localhost:5000

### 环境变量说明

| 变量 | 说明 | 必填 |
|------|------|------|
| `SECRET_KEY` | JWT 签名密钥 | 是 |
| `LLM_PROVIDER` | 文本模型提供商（deepseek / openai / dashscope） | 是 |
| `LLM_API_KEY` | 文本模型 API Key | 是 |
| `LLM_MODEL` | 文本模型名称 | 是 |
| `LLM_BASE_URL` | 文本模型 API 地址 | 否 |
| `LLM_VISION_PROVIDER` | 视觉模型提供商（ark / deepseek） | 否 |
| `LLM_VISION_API_KEY` | 视觉模型 API Key | 否 |
| `LLM_VISION_MODEL` | 视觉模型名称 | 否 |

> 未配置 API Key 时自动进入 Mock 模式，可体验完整交互流程。

---

## 📁 项目结构

```
diagnosis-app/
├── app.py                  # 应用入口
├── config.py               # 配置管理
├── requirements.txt        # 依赖清单
├── .env.example            # 环境变量示例
├── ai/                     # AI 模块
│   ├── llm.py              # LLM 调用层（含流式 + JSON 解析）
│   ├── diagnosis.py        # 错题诊断引擎
│   ├── rag.py              # RAG 检索增强
│   └── knowledge_tracing.py # BKT 知识追踪
├── models/                 # 数据模型
│   ├── database.py         # 数据库初始化 + 知识图谱数据
│   └── question_bank.py    # 预置题库
├── routes/                 # 路由（9个蓝图）
│   ├── auth.py
│   ├── diagnosis.py
│   ├── practice.py
│   ├── history.py
│   ├── dashboard.py
│   ├── ocr.py
│   ├── chat.py
│   ├── teacher.py
│   └── upload.py
├── utils/                  # 工具函数
│   ├── auth.py             # JWT 认证
│   ├── cache.py            # 内存缓存
│   ├── rate_limit.py       # 接口限流
│   ├── errors.py           # 错误处理
│   └── logger.py
├── static/                 # 静态资源
│   ├── css/style.css
│   └── js/app.js
└── index.html              # 单页应用入口
```

---

## 🎯 使用说明

### 学生端
1. 注册 / 登录（学生角色）
2. 录入错题：拍照上传 OCR 识别 或 手动输入
3. 点击「定位这次错误」，等待 AI 诊断
4. 查看诊断报告：错误原因、薄弱点、掌握度、学习路径
5. 开始针对性练习，验证掌握情况
6. 在学习看板查看整体进度，在知识图谱探索知识体系

### 教师端
1. 注册时选择「教师」角色
2. 创建班级，获取班级码
3. 学生加入班级后，查看班级学情分析

---

## 📄 License

MIT License

---

**知径** · 让每一道错题都成为进步的起点
