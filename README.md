# 研途智学

面向考研群体的个性化学习规划与知识追踪系统。前后端分离：Vue 3 前端 + FastAPI / SQLAlchemy / SQLite 后端。

## 当前进度

- **M1 工程整理**：目录规范、`.gitignore`、README、TypeScript 编译产物修正
- **M2 后端基础**：用户认证、考试目标、科目与知识点、学习任务、学习记录、错题、掌握度追踪、AI 计划与错题分析
- **M3 前后端联调（已完成）**：
  - 登录 / 注册页，JWT 持久化与自动恢复会话
  - 统一 API 客户端（`src/api`），Vite `/api` 代理
  - 总览、任务、知识追踪、错题本、备考计划五个页面全部接入真实接口
  - 任务增删改查、开始 / 暂停 / 完成（写入学习记录并更新掌握度）
  - 知识点练习录入、错题录入 / 筛选 / 状态流转 / AI 分析
  - 备考目标表单、阶段时间轴、本周目标（可增删勾选）、执行洞察
  - 移除 localStorage 演示数据与所有“只弹提示”的假按钮
- **M4（待做）**：BKT / 间隔复习规则、真实大模型结构化输出校验、部署与答辩材料

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
├── src/
│   ├── api/                # 请求客户端与类型定义
│   ├── stores/             # 会话、提示、科目/知识点缓存
│   ├── components/         # 弹窗与表单组件
│   ├── pages/              # 登录、总览、任务、知识、错题、计划
│   ├── App.vue             # 应用外壳、导航与登录守卫
│   └── style.css
├── backend/
│   ├── app/
│   │   ├── api/routes/     # HTTP 路由
│   │   ├── core/           # 配置与安全
│   │   ├── db/             # 数据库会话与演示数据
│   │   ├── models/         # SQLAlchemy 数据模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   └── services/       # 掌握度、调度、AI 服务
│   └── tests/              # 接口与核心流程测试
└── README.md
```

## 启动方式

先启动后端（前端所有页面都依赖 API）：

```powershell
cd E:\software
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

接口文档：http://localhost:8000/docs

再启动前端：

```powershell
cd E:\software
npm run dev
```

默认地址：http://localhost:5173

> 前端默认通过 Vite 代理把 `/api` 转发到 `http://127.0.0.1:8000`，无需额外配置 CORS。
> 如需直连其它后端，可设置 `VITE_API_BASE=http://host:port/api`。
> 若终端里没有 `npm`，可使用 `node node_modules\vite\bin\vite.js --port 5173`。

首次安装依赖：

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## 演示账号

```text
用户名：demo
密码：demo1234
```

后端启动时会自动建表；空库时写入演示数据。演示账号跨天启动时会自动补齐当天的 5 条任务，避免“今日任务”为空。

## 功能说明

| 模块 | 能力 |
|---|---|
| 登录 / 注册 | 注册即创建考试目标与知识点基础状态；登录状态保存在本地 token，刷新不掉线 |
| 学习总览 | 今日时长、完成率、平均掌握度、连续学习、今日任务、薄弱点推荐、周学习节奏 |
| 今日任务 | 按日期 / 状态 / 科目筛选；新建、编辑、删除、开始 / 暂停、完成（记录正确率、自评、备注） |
| 知识追踪 | 掌握度排序、趋势、练习次数；记录练习后按正确率与自评更新掌握度 |
| 错题本 | 录入、按状态 / 科目筛选、标记掌握、删除；单题 AI 分析与建议；按错误类型自动汇总 |
| 备考计划 | 根据考试日期自动生成四阶段时间轴；本周目标增删勾选；执行洞察；AI 重排任务 |
| 备考目标 | 考试日期、院校、专业、目标分数、每日学习时长 |

## 核心业务链路

```text
登录
→ 读取考试目标与今日任务
→ 开始 / 完成任务并写入学习记录
→ 按正确率和自评更新知识点掌握度
→ 重新计算薄弱知识点与任务优先级
→ AI 生成计划说明、错题分析或每日总结
```

任务优先级采用可解释规则：知识点重要度、掌握度、逾期天数和距离考试时间共同决定。AI 负责解释与建议，调度规则负责保证结果可校验。

## 主要接口

```text
POST   /api/auth/register | /api/auth/login       认证
GET    /api/auth/me
GET    /api/goals/current | PUT /api/goals/current 备考目标
GET    /api/subjects                              科目
GET    /api/tasks?date=YYYY-MM-DD                 当日任务
POST   /api/tasks | PATCH/DELETE /api/tasks/{id}  任务管理
POST   /api/tasks/{id}/start | /complete          开始 / 完成
GET    /api/knowledge                             知识点掌握度
POST   /api/knowledge/{id}/practice               练习记录
GET    /api/wrong-questions                       错题列表
POST   /api/wrong-questions | PATCH/DELETE ...    错题管理
POST   /api/wrong-questions/{id}/analyze          AI 错题分析
GET    /api/dashboard                             总览聚合
GET    /api/plan                                  计划、阶段、周目标与洞察
POST   /api/plan/goals | PATCH/DELETE ...         周目标管理
POST   /api/ai/plan | /api/ai/summary             AI 计划 / 每日总结
```

## 运行测试

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
```

当前覆盖：登录注册、目标与知识点初始化、仪表盘、任务完成与掌握度更新、练习记录、AI 计划、错题分析、计划阶段与周目标、任务换绑科目/知识点。

## 环境变量

复制 `backend/.env.example` 为 `backend/.env`，至少修改 `SECRET_KEY`（建议 32 个字符以上）。

```text
AI_PROVIDER=local              # local 使用可解释规则，openai 调用兼容接口
OPENAI_API_KEY=                # 不要提交到 Git
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173
SEED_DEMO=true
```

默认数据库位置为 `backend/data/app.db`，不需要额外配置。

如果 AI 接口调用失败，后端会自动回退到本地规则，不影响任务规划和学习记录。
