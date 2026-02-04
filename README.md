# 目标节拍 (Pacer AI)

<p align="center">
  <img src="logo.png" alt="目标节拍 Logo" width="120">
</p>

<p align="center">
  <b>智能目标节奏管理工具</b><br>
  用自然语言设定目标，AI 智能拆解，日历可视化追踪
</p>

---

## ✨ 核心功能

| 功能 | 描述 |
|------|------|
| 🗣️ **自然语言解析** | 输入 "2月10号前完成PPT" → 自动识别日期和任务 |
| 📅 **日历可视化** | 月历视图展示所有目标，一目了然 |
| ✅ **智能 Checklist** | AI 自动拆解目标为可执行的子任务 |
| 📊 **Review Dashboard** | KPI 分析、状态分布、Drill-down 交互 |
| 📤 **数据导出** | 一键导出 CSV，支持周报/月报/年报 |

---

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Google Gemini API Key

### 安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/pacer-ai.git
cd pacer-ai

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
# 创建 .env 文件并添加：
GEMINI_API_KEY=your_api_key_here

# 4. 运行应用
streamlit run app.py
```

### 在线演示
🔗 **Demo**: [https://pacer-ai.streamlit.app](https://pacer-ai.streamlit.app)

---

## 📦 技术栈

- **Frontend**: Streamlit
- **Charts**: Plotly
- **Data**: Pandas
- **AI**: Google Gemini API
- **NLP**: dateparser (多语言日期解析)

---

## 🎯 使用场景

- **个人目标管理**: 新年计划、学习目标、健身计划
- **项目跟踪**: 小型项目里程碑管理
- **习惯养成**: 可视化追踪完成进度
- **复盘分析**: Review Dashboard 辅助周报/月报

---

## 📁 项目结构

```
pacer-ai/
├── app.py              # 主应用入口
├── review.py           # Review Dashboard 模块
├── persistence.py      # 数据持久化
├── utils.py            # 工具函数 (AI 解析)
├── requirements.txt    # 依赖列表
├── .env                # 环境变量 (需自行创建)
├── logo.png            # 项目 Logo
└── README.md           # 项目说明
```

---

## 📄 License

MIT License - 自由使用、修改和分发

---

## 🙏 致谢

- [Streamlit](https://streamlit.io) - 快速构建数据应用
- [Google Gemini](https://ai.google.dev) - 强大的 AI 能力
- [Plotly](https://plotly.com) - 交互式可视化

---

<p align="center">
  Made with ❤️ for Hackathon
</p>
