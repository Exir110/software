# 研途智学

面向考研群体的个性化学习规划与知识追踪系统。项目采用前后端分离结构，当前已完成 Vue 前端原型和 FastAPI + SQLite 后端基础。

## 当前进度

- M1 工程整理：目录规范、`.gitignore`、README、TypeScript 编译产物修正
- M2 后端基础：用户认证、考试目标、科目与知识点、学习任务、学习记录、错题、掌握度追踪、AI 计划与错题分析
- 前端仍使用本地演示数据，尚未切换到后端 API（下一阶段 M3）

## 技术栈

```text
前端：Vue 3 + TypeScript + Vite
后端：FastAPI + SQLAlchemy 2 + SQLite
认证：JWT + PBKDF2 密码哈希
测试：pytest + FastAPI TestClient
AI：OpenAI 兼容接口，默认使用本地规则降级
```

## 目录结构

```text
.
├── src/                     # Vue 前端
├── backend/
│   ├── app/
│   │   ├── api/routes/      # HTTP 路由
│   │   ├── core/            # 配置与安全
│   │   ├── db/              # 数据库会话与演示数据
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   └── services/        # 掌握度、调度、AI 服务
│   └── tests/               # 接口与核心流程测试
└── README.md
```

## 启动前端

```powershell
npm install
npm run dev
```

默认地址：http://localhost:5173

## 启动后端

首次运行先创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

启动 API：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

接口文档：http://localhost:8000/docs

后端启动时会自动建表，并在空数据库中写入演示数据。

## 演示账号

```text
用户名：demo
密码：demo1234
```

## 运行测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
```

测试覆盖登录、目标与知识点初始化、仪表盘、任务完成与掌握度更新、练习记录、AI 计划、错题分析。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，至少修改 `SECRET_KEY`（建议 32 个字符以上）。

```text
AI_PROVIDER=local              # local 使用可解释规则，openai 调用兼容接口
OPENAI_API_KEY=                # 不要提交到 Git
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

默认数据库位置为 `backend/data/app.db`，不需要额外配置。`.env.example` 中的 `DATABASE_URL` 默认保持注释。

如果 AI 接口调用失败，后端会自动回退到本地规则，不影响任务规划和学习记录。

## 核心业务链路

```text
登录
→ 读取考试目标与今日任务
→ 完成任务并写入学习记录
→ 按正确率和自评更新知识点掌握度
→ 重新计算薄弱知识点与任务优先级
→ AI 生成计划说明、错题分析或每日总结
```

任务优先级采用可解释规则：知识点重要度、掌握度、逾期天数和距离考试时间共同决定。AI 负责解释与建议，调度规则负责保证结果可校验。

## 后续计划

- M3：前端拆分组件并接入真实 API，移除 `localStorage` 演示数据
- M4：完善 BKT/间隔复习规则，接入真实大模型并增加结构化输出校验
- M5：补充接口文档、测试报告、部署配置和答辩材料
