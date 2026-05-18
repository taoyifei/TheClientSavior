# The Client Savior｜客户拯救者

“客户拯救者”是面向一线客服和现场经理的客户挽留工作台。新版主界面已经从 Streamlit Demo 迁移为 **FastAPI 后端 + React/Vite/TypeScript + Ant Design 前端**。

核心链路仍然保留原有 Python 智能体：

```text
客户投诉 + 客户画像
→ 本地政策召回
→ 云端 LLM 生成
→ 失败时本地模板兜底
→ 返回客户分析、推荐政策、四段式话术、内部提醒
```

## 设计边界

- 不使用本地大模型。
- 不使用向量数据库。
- 不使用 LangChain、LlamaIndex。
- 不引入数据库，演示版使用本地 JSON + 后端内存看板。
- 手机号只用于本地客户查询和看板记录，不传给 LLM。
- 页面、CSV、Markdown 默认只展示脱敏手机号。

## 新版启动方式

### 一键启动（推荐）

Windows PowerShell 进入项目根目录后运行：

```powershell
cd "D:\Github\The Client Savior"
powershell -ExecutionPolicy Bypass -File .\start_all.ps1
```

脚本会自动：

- 检查并复用 `.venv` 里的 Python；
- 首次启动时安装前端 `npm install`；
- 启动 FastAPI 后端 `0.0.0.0:8000`；
- 启动 Vite 前端 `0.0.0.0:5173`；
- 打印本机和局域网访问地址。

启动后访问：

```text
http://localhost:5173
```

同局域网访问时，用脚本打印的局域网地址，例如：

```text
http://192.168.1.5:5173
```

保持启动窗口打开；按 `Ctrl+C` 可结束本脚本启动的后台任务。

### 1. 后端环境

如果已经有根目录 `.venv`，直接安装后端依赖：

```powershell
cd "D:\Github\The Client Savior"
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

没有虚拟环境时：

```powershell
cd "D:\Github\The Client Savior"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填写 `DASHSCOPE_API_KEY`：

```powershell
Copy-Item .env.example .env
```

默认配置：

```env
DASHSCOPE_API_KEY=替换成你的阿里云百炼或 DashScope API Key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-flash
LLM_TIMEOUT=6
LLM_MAX_TOKENS=800
```

未配置有效 API Key 时，后端不会崩溃，会自动返回“本地模板兜底”结果。

### 3. 启动后端

```powershell
.\start_backend.ps1
```

等看到后端监听：

```text
http://127.0.0.1:8000
```

### 4. 启动前端

新开一个 PowerShell：

```powershell
.\start_frontend.ps1
```

浏览器访问：

```text
http://localhost:5173
```

同局域网访问时，使用前端机器的局域网 IP，例如：

```text
http://192.168.1.250:5173
```

后端脚本默认监听 `0.0.0.0:8000`，前端脚本默认监听 `0.0.0.0:5173`。

## 常用脚本

```powershell
# 一键启动前后端
powershell -ExecutionPolicy Bypass -File .\start_all.ps1

# 只启动后端
.\start_backend.ps1

# 只启动前端
.\start_frontend.ps1
```

## 自检命令

后端核心：

```powershell
python -m compileall backend src scripts
python scripts\smoke_test.py
```

前端构建：

```powershell
cd frontend
npm install
npm run build
```

API 冒烟测试需要先启动后端：

```powershell
python scripts\api_smoke_test.py
```

期望输出：

```text
smoke_test_ok
api_smoke_test_ok
```

## 主要接口

- `GET /api/health`：健康检查。
- `GET /api/config`：LLM 配置状态。
- `POST /api/llm/test`：LLM 连通性测试。
- `GET /api/policies`：政策库。
- `GET /api/demo-cases`：演示案例。
- `GET /api/customers/lookup?phone=...`：本地客户画像查询。
- `POST /api/generate`：生成客户挽留方案。
- `GET /api/dashboard`：后台风险看板。
- `POST /api/dashboard/reset`：清空本次看板。
- `GET /api/dashboard/export`：导出脱敏 CSV。

## 演示工作台说明

新版前端按“中国移动客服挽留工作台”组织页面：

1. 顶部标题居中强化，适合现场 Demo 投屏。
2. “客服工作台”第一入口是号码查询，手机号只用于本地画像查询和本次看板记录。
3. 热门场景保留高频演示入口，例如套餐太贵、流量不够、换手机、家庭号码多。
4. 客户 360 优先展示手机号、当前套餐、当前月租、客户类型、网龄、携转风险等关键字段。
5. AI 决策驾驶舱突出首推业务、是否超套、风险等级和跟进优先级。
6. 投诉录入区的语音输入按钮当前为占位能力，悬浮提示“开发中，敬请期待”。
7. 风险看板默认按风险等级排序，并支持筛选、手机号后四位搜索和脱敏 CSV 导出。

界面中统一使用“超套”描述套餐外流量或费用风险；LLM 状态、模型名称、本次处理数等系统运行信息放在右侧运行状态栏，避免抢占业务主视觉。

## 号码查询逻辑

系统号码查询分两级：

1. 先查 `data/customers.json` 中的本地演示客户画像。
2. 若未命中，但该手机号本次已经生成过挽留方案并进入风险看板，则从本次风险看板内存记录回填画像。
3. 若仍未命中，允许客服手动补充画像继续生成方案。

本次风险看板记录只保存在后端进程内存中，重启后会清空。完整手机号只用于后端内存匹配，不返回前端，不写入 CSV/Markdown，也不会传给 LLM。

## 文件结构

```text
.
├── backend/
│   ├── main.py
│   ├── schemas.py
│   ├── requirements.txt
│   └── services/
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
├── src/
│   ├── agent.py
│   ├── llm_client.py
│   ├── matcher.py
│   ├── models.py
│   └── templates.py
├── data/
│   ├── policies.json
│   ├── demo_cases.json
│   └── customers.json
├── scripts/
│   ├── smoke_test.py
│   └── api_smoke_test.py
├── app.py
├── app_streamlit_legacy.py
├── start_all.ps1
├── start_backend.ps1
└── start_frontend.ps1
```

## Legacy Streamlit

`app.py` 和 `app_streamlit_legacy.py` 仅作为旧版 Streamlit 备份，不再是主入口。新版演示请使用：

```text
backend/ + frontend/
```

## 费用安全提醒

建议在阿里云百炼控制台开启“免费额度用完即停”。额度耗尽后接口会返回类似 `AllocationQuota.FreeTierOnly` 的错误，项目会按 LLM 调用失败处理并切换到本地模板兜底，避免继续产生调用费用。
