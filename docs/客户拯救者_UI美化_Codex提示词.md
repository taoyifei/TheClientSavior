# 客户拯救者 UI 与操作体验美化｜Codex 提示词

你现在要继续修改一个 Streamlit 项目：**The Client Savior｜客户拯救者**。

目标：在不改变核心算法链路的前提下，把页面改成更适合现场演示的“产品级 Demo”。项目必须继续保持轻量、可在普通笔记本电脑上运行，不引入本地大模型、向量库、LangChain、LlamaIndex 或重型前端框架。

当前核心链路已经可用：

```text
投诉内容 + 客户画像
        ↓
本地政策规则召回 Top 5
        ↓
云端 LLM 生成客户分析、Top 3 政策、挽留话术、内部提醒
        ↓
LLM 失败或无 Key 时本地模板兜底
        ↓
Streamlit 页面展示
```

请只做 UI、交互、导出和演示流程增强，不要重写核心业务逻辑。

---

## 一、总体要求

1. 保持现有文件结构：
   - `app.py`
   - `src/agent.py`
   - `src/llm_client.py`
   - `src/matcher.py`
   - `src/models.py`
   - `src/templates.py`
   - `data/policies.json`
   - `data/demo_cases.json`
   - `scripts/smoke_test.py`

2. 重点修改 `app.py`，必要时只在 `src/` 内增加很小的纯函数，不要影响核心链路。

3. 不要新增重型依赖。`requirements.txt` 仍然只保留：
   ```text
   streamlit>=1.50.0
   openai>=1.0.0
   python-dotenv>=1.0.0
   ```

4. UI 必须是中文，适合中国移动培训现场演示。

5. 页面不要出现“LLM 智能生成”旧文案，统一使用：
   - `云端模型生成`
   - `本地模板兜底`

6. 不要删除侧边栏 LLM 连通性测试。

7. 不要删除“AI 投诉处理 / 管理看板 / 政策库”三个 Tab。

8. 所有核心按钮都要避免误操作：
   - 空投诉不能生成。
   - 生成过程中显示明确 spinner。
   - LLM 失败时仍展示兜底结果。

9. 修改后必须通过：
   ```bash
   python -m compileall app.py src scripts
   python scripts/smoke_test.py
   ```

---

## 二、视觉风格

请在 `app.py` 增加 `_inject_css()`，用 `st.markdown(..., unsafe_allow_html=True)` 注入少量 CSS。

设计风格：

- 清爽、现代、企业级。
- 主色：移动蓝 / 深蓝。
- 辅色：绿色表示云端模型成功，橙色表示本地兜底，高风险用红色。
- 卡片化展示，减少纯文字堆叠。
- 大标题区域有产品 slogan。
- 重要状态用 badge / pill 显示。

CSS 建议支持这些类：

```text
.hero-card
.hero-title
.hero-subtitle
.step-card
.status-pill
.status-llm
.status-fallback
.risk-high
.risk-medium
.risk-low
.policy-card
.policy-rank
.policy-title
.policy-meta
.chip
.script-card
.note-card
.copy-box
```

注意：不要让 CSS 影响 Streamlit 默认表单无法点击，不要写复杂 JS。

---

## 三、首页顶部改造

当前页面只有标题和 caption。请改成更像产品首页的 Hero 区域。

新增 `_render_hero()`：

展示内容：

```text
The Client Savior｜客户拯救者
投诉秒变留人机会，政策套餐自动配对

三步完成：录入投诉 → 云端模型分析 → 生成挽留方案
```

Hero 区下方增加 3 个步骤卡片：

1. `① 输入投诉`：粘贴客户原话，选择基础画像。
2. `② 模型分析`：本地召回政策，云端模型生成方案。
3. `③ 一线执行`：输出推荐政策、挽留话术、办理提醒。

---

## 四、AI 投诉处理 Tab 操作优化

当前是“选择演示案例 + 一键填充 + 表单”。请改成更适合演示的布局。

### 4.1 布局

`AI 投诉处理` Tab 使用左右两栏：

```text
左侧：客户输入区，占 40%
右侧：结果展示区，占 60%
```

左侧放：

- 演示案例按钮区
- 投诉内容输入框
- 客户画像输入
- 生成按钮
- 清空 / 处理下一条按钮

右侧放：

- 未生成时显示“等待生成”的引导卡片
- 已生成时显示分析结果、政策推荐、话术、内部提醒

### 4.2 演示案例按钮

不要只用 selectbox。请新增 `_render_demo_case_buttons(demo_cases)`：

- 使用 2 列或 3 列按钮展示案例名称。
- 每个按钮点击后自动填充投诉和画像。
- 按钮文案短一点，如：
  - 套餐太贵想携转
  - 流量不够刷视频
  - 宽带 WiFi 差
  - 想换手机
  - 家庭号码多
  - 商户宽带宣传

保留 selectbox 也可以，但按钮必须有。

### 4.3 客户画像简化

把客户画像改成更直观的“客户标签 + 关键参数”。

表单顺序建议：

1. 投诉内容 `st.text_area`
2. 当前月租 `st.number_input`
3. 客户类型 `st.selectbox`
4. 网龄 `st.slider` 或 `st.number_input`
5. 家庭号码数 `st.slider`
6. 勾选项：
   - 已有宽带
   - 有换机需求
   - 明确想离网/携转
   - 启用云端模型生成

### 4.4 操作按钮

生成按钮文案改为：

```text
🚀 生成挽留方案
```

新增按钮：

```text
🧹 清空输入
```

`清空输入` 需要清空投诉、重置画像、清空 last_result，不影响历史看板。

---

## 五、结果展示美化

当前结果展示是：模式提示 + 三个 metric + 客户分析 + expander 政策 + markdown 话术。请改成更像产品结果页。

### 5.1 顶部结果摘要卡

新增 `_render_result_summary(result)`：

顶部展示 4 个小卡片：

1. 当前模式：云端模型生成 / 本地模板兜底
2. 风险等级：高 / 中 / 低
3. 投诉类型
4. 耗时：x.xx 秒

模式 badge：

- 云端模型生成：绿色
- 本地模板兜底：橙色

风险 badge：

- 高：红色
- 中：橙色
- 低：绿色

如果 `result.llm_error` 有值，显示一个浅黄色提示条：

```text
云端模型调用异常，已切换本地模板兜底：xxx
```

### 5.2 客户分析卡

新增 `_render_customer_analysis_card(analysis)`：

展示：

- 投诉类型
- 情绪
- 风险等级
- 关键诉求 chips
- 摘要

关键诉求用 chip 样式展示，而不是纯文本。

### 5.3 推荐政策卡片

改造 `_render_recommended_policies()`：

不要默认用 expander 作为主展示。请把 Top 3 政策以卡片形式展示：

每张卡包含：

- 排名角标，如 `TOP 1`
- 政策名称
- 分类 / 价格
- 本地匹配分
- 推荐理由
- 一句话卖点
- 核心权益 chips，最多显示 4 个
- 风险提醒，最多显示 2 个

办理条件和详细政策可放在 expander：

```text
查看办理条件与风险说明
```

### 5.4 挽留话术卡片

改造 `_render_retention_script()`：

四段话术分别做成卡片：

1. 安抚开场
2. 方案介绍
3. 风险说明
4. 下一步引导

在话术区域下方增加一个完整话术文本框或 `st.code`：

```text
【安抚开场】...
【方案介绍】...
【风险说明】...
【下一步引导】...
```

再增加 `st.download_button`：

```text
下载方案 Markdown
```

下载内容由新增函数 `build_result_markdown(result)` 生成，包含：

- 客户分析
- 推荐政策 Top 3
- 四段式话术
- 内部提醒
- 生成模式、模型、耗时

文件名建议：

```text
client_savior_result.md
```

### 5.5 内部提醒

把内部提醒改为浅蓝或浅黄卡片，不要全部用 `st.info` 堆叠。

新增 `_render_note_cards(notes)`。

---

## 六、管理看板美化

当前看板已经有指标和柱状图。请增强展示但不要加复杂依赖。

要求：

1. 顶部 5 个指标保留：
   - 已处理投诉数
   - 高风险客户数
   - 云端模型生成次数
   - 本地模板兜底次数
   - 平均耗时

2. 增加一个“演示转化漏斗 / 处理流程”文本卡：

```text
输入投诉 → 政策召回 → 模型生成 → 一线执行
```

3. 历史明细表增加一列：
   - 推荐政策 Top 1

如果当前 history 没有这个字段，请在 `_update_dashboard()` 里加入。

4. 不要引入 pandas；继续使用 list/dict + st.dataframe 即可。

---

## 七、政策库 Tab 美化

当前政策库是搜索 + 分类 + expander。请增强：

1. 顶部增加统计：
   - 政策卡数量
   - 分类数量
   - 当前筛选结果数量

2. 增加“分类快捷筛选按钮”。

3. 每张政策卡展示：
   - ID
   - 标题
   - 分类 badge
   - 价格
   - 目标客户
   - 核心权益 chips

4. 搜索仍然支持政策名、关键词、适用场景。

---

## 八、侧边栏优化

侧边栏分成三块：

1. `运行状态`
   - LLM 状态
   - 当前模型
   - 超时时间
   - 连通性测试按钮

2. `演示统计`
   - 云端模型生成次数
   - 本地模板兜底次数
   - 总处理数

3. `现场提示`
   - 如果 Key 未配置，显示：`未配置有效 API Key 时系统会走本地模板兜底。`
   - 如果 Key 已配置，显示：`推荐先点击连通性测试，确认云端模型可用。`

---

## 九、保留和补充稳定性

在 UI 改造过程中，继续保留以下逻辑：

1. `data/policies.json` 缺失时友好提示并 `st.stop()`。
2. `data/demo_cases.json` 缺失时允许页面继续运行。
3. 生成时如果投诉为空，提示用户输入。
4. LLM 失败时进入 fallback。
5. 页面继续展示：
   - 当前模式
   - 模型名称
   - 耗时
   - 缓存状态
   - 失败原因

---

## 十、建议新增函数

请在 `app.py` 中新增或改造以下函数：

```python

def _inject_css() -> None: ...
def _render_hero() -> None: ...
def _render_step_cards() -> None: ...
def _render_demo_case_buttons(demo_cases: list[dict[str, object]]) -> None: ...
def _clear_current_case() -> None: ...
def _render_result_placeholder() -> None: ...
def _render_result_summary(result: AgentResult) -> None: ...
def _render_status_badge(text: str, kind: str) -> str: ...
def _render_customer_analysis_card(analysis: dict[str, object]) -> None: ...
def _render_policy_card(item: dict[str, object]) -> None: ...
def _render_script_cards(script: dict[str, str]) -> None: ...
def _render_note_cards(notes: list[str]) -> None: ...
def build_result_markdown(result: AgentResult) -> str: ...
def _format_list_items(value: object, limit: int | None = None) -> list[str]: ...
```

注意：如果使用 `unsafe_allow_html=True`，所有展示内容都要先做 `html.escape()`，避免客户投诉内容或 LLM 输出中含 HTML 导致页面问题。

---

## 十一、验收标准

完成后自检：

```bash
python -m compileall app.py src scripts
python scripts/smoke_test.py
streamlit run app.py
```

页面验收：

1. 首页顶部有 Hero 区和三步说明。
2. AI 投诉处理页可以通过案例按钮一键填充。
3. 点击“🚀 生成挽留方案”后，右侧展示产品化结果页。
4. 推荐政策以卡片形式展示，不只是 expander。
5. 挽留话术有四段式卡片和 Markdown 下载按钮。
6. 管理看板指标正常累计。
7. 政策库能搜索、分类筛选、卡片展示。
8. 无 API Key 时仍能生成本地模板兜底结果。
9. 有 API Key 且连通正常时默认显示“云端模型生成”。
10. 不出现 1~2 分钟无响应；超时后自动切换兜底。

---

## 十二、不要做的事

不要做这些：

1. 不要接入本地大模型。
2. 不要引入 LangChain / LlamaIndex / 向量库。
3. 不要把 Word / Excel 解析放到页面运行时。
4. 不要删除本地兜底。
5. 不要把所有政策原文塞给 LLM。
6. 不要用复杂 JS 复制按钮，优先用 `st.code` 和 `st.download_button`。
7. 不要改动 `data/policies.json` 字段结构。
8. 不要改动 `AgentResult` 主字段结构。

最终目标：这个页面要看起来像一个可以现场汇报的 AI 产品，而不是普通 Streamlit 表单。
