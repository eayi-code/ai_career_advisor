# antigravity-build 分支更新记忆文件

该记忆文件用于记录 `antigravity-build` 分支上针对 **AI职业决策支持系统** 的所有交互细节、容灾恢复以及流式优化等方面的更新情况，以方便后续的迭代与开发。

---

## 一、 更新概述

在 `antigravity-build` 分支中，主要针对系统的交互体验、流式输出、数据库异常自愈以及打断（Stop）逻辑进行了重构，完成了以下关键提升：
1. **多智能体流式推理（SSE）**：打通了 LangChain 框架与前端 SSE 通信，实现了实时 Token 级别推理和步骤状态展示。
2. **连接打断（Stop）优雅退出**：解决了用户中途点击“停止生成”后，后端不断重试、触发降级策略并抛出大量 Traceback 报错的异常问题。
3. **多轮对话 DOM 冲突修复**：解决了在同一次对话中连续提问时，流式输出覆盖首个对话框的 Bug。
4. **SQLAlchemy 事务自愈**：修复了 Agent 重试时由于之前的 SQL 报错未回滚引发 of `PendingRollbackError`。
5. **Marked.js 精美 Markdown 渲染**：引入专业 Markdown 渲染库，完美呈现代码块、 zebra 条纹表格和有序/无序列表。
6. **火狐浏览器（Firefox）兼容性修复**：修复了在 Firefox 下因使用非标准 `window.event` 导致无法切换 Agent 的 Bug。
7. **全局推理弹窗数据恢复**：解决了用户切换界面返回或加载历史对话后，全局“推理详情”侧边栏内容变为空白占位符的 Bug。
8. **ChatGPT/Gemini 风格的自增长输入框 (Auto-grow Textarea)**：将单行 Input 替换为多行 Textarea，支持 Shift+Enter 换行、Enter 快捷发送，输入框高度可随输入字数自增长。
9. **智能防抖滚动定位 (Smart Autoscroll)**：流式生成过程中智能判断用户滚动位置。若用户手动向上滚动查看历史记录，则暂停强制滚屏，防止页面跳动影响阅读。
10. **流式光标与代码块一键复制**：流式生成末尾增加了脉冲打字光标；使用 `marked` 扩展了代码渲染器，实现精美的深色代码块排版、编程语言标识及一键“复制代码”功能。
11. **五大高端前端交互动效升级**：实现欢迎卡片3D视差倾斜、文件拖拽磁吸 snap 上传、折叠展开推理面板、气泡 staggered 延迟滑入，以及个人中心完善度环图渐进绘制与数字跳动计数，全面提升系统的高级感。

---

## 二、 核心变更详解

### 1. 流式输出与打断信号重构 (SSE & Abort)
* **变更点**：
  * 定义了 `ClientDisconnectedError(BaseException)`（位于 [base_agent.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/base_agent.py)），该异常继承自 `BaseException` 级别而非 `Exception`。
  * 当用户在前端点击“停止”或关闭页面时，SSE 生成器 `generate` 的 `finally` 块触发，从而删除 `ChatService._sse_task_queues` 中的对应 `task_id`。
  * `on_step_callback` 和 `on_token_callback` 在回调执行时检查到 `task_id` 不存在，直接抛出 `ClientDisconnectedError`。
* **设计优势**：
  * 因为 `ClientDisconnectedError` 继承自 `BaseException`，它**能够穿透** LangChain 内部 of Exception 捕获机制、Agent 内部的 `try...except Exception` 重试循环以及编排器的降级逻辑，使执行线程直接中断退出。
  * 后台线程 `run_agent()` 在 [chat_service.py](file:///d:/Opencode_workplace/ai_career_advisor/app/services/chat_service.py) 中显式捕获该异常，并直接 `return` 退出，仅输出一条干净的日志，彻底消除了 Traceback 堆栈报错信息。

### 2. 多轮对话 DOM 相对定位 (Multi-Turn Chat Isolation)
* **变更点**：
  * 过去前端在追加流式回复文本时，使用的是静态 `document.getElementById('loadingContent')` 类似全局选择器。在多轮对话中，DOM 内会存在多个同名 ID 容器，导致流式内容总是灌入第一轮的对话框中。
  * **修复方案**：在 [chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) 中引入全局变量 `activeLoadingBubble`，在每次发送新消息并生成新的消息泡泡后，将该泡泡 of DOM 对象赋值给 `activeLoadingBubble`。所有流式渲染方法（`appendStreamContent`, `updateLiveSteps` 等）均使用相对选择器 `activeLoadingBubble.querySelector(...)` 范围限制，确保多轮对话内容精准定位到当前的最新泡泡。

### 3. SQLAlchemy 事务重置 (PendingRollbackError Repair)
* **变更点**：
  * 过去当 Agent 中的某次 SQL 查询操作引发错误时，数据库 Session 处于 Invalid 状态。由于未进行 Rollback，当 Agent 进行第 2/3 次重试或触发编排器降级策略时，再次执行 SQL 会直接引发 `sqlalchemy.exc.PendingRollbackError`。
  * **修复方案**：在 [base_agent.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/base_agent.py) 中的 `run()` 以及 [orchestrator.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/orchestrator.py) 中的 `_execute_single_agent()` 的异常捕获块中，加入了显式的 `db.session.rollback()`。确保每次出现数据库级别错误时都会彻底回滚，不污染后续的重试行为。

### 4. 专业级 UI/UX 优化 (Markdown Rendering & Input Styling)
* **Markdown 渲染**：废弃了原有的正则表达式简易解析器，在 [base.html](file:///d:/Opencode_workplace/ai_career_advisor/app/templates/base.html) 引入了 `marked.js`。在 [chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) 中使用 `marked.parse` 解析推理内容，并在 [chat.css](file:///d:/Opencode_workplace/ai_career_advisor/app/static/css/chat.css) 中对表格、列表、标题和代码块进行了专业的美化样式编写，支持响应式横向滚动及斑马纹美化。
* **禁用状态高保真**：在 Agent 输出过程中，前端输入框容器会加上 `.disabled` 类，整体背景变灰、鼠标变为 `not-allowed` 样式，发送和文件上传按钮半透明且不可点击，从视觉和逻辑上防止用户在生成期间二次提交。
* **自增长输入框 (Textarea Auto-grow)**：聊天输入框转为 Textarea。在 `initChatPage` 和 `sendMessage` 中添加了对 `input` 事件的监听和高度调整脚本，高度会在 `40px` 到 `160px` 之间自增长，并且拦截 `Enter` 实现无刷新快捷发送，支持 `Shift+Enter` 原生换行。
* **流式打字光标 (Streaming Cursor)**：在流式生成中，给正在输出内容的 `.message-content` 容器附加上 `.streaming-active` 伪类，以展示闪烁的墨色方块光标，模拟 ChatGPT/Gemini 风格的实时书写质感。在生成终态（无论是完成、中止还是出错）时自动剔除此光标。
* **智能防抖滚动 (Smart Autoscroll)**：在 [chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) 中定义了 `smartScrollToBottom`。滚动高度距离底部阈值小于 `150px` 时才进行自动贴底滚屏，如果用户手动向上拉查看历史数据，贴底滚动会自动暂停，极大优化了连续阅读的连贯性。
* **ChatGPT 风格代码块一键复制**：覆盖了 `marked` 默认的代码块（code block）解析逻辑。流式渲染时将代码包裹至自定义的 `.code-block-wrapper`，生成顶部灰色工具栏展示编程语言，并在右侧绑定 `copyCodeBlock` 复制代码与“已复制！”状态转换动画，实现了生产级的一键复制代码体验。

### 5. 全局推理弹窗数据恢复 (Side Panel Reasoning Restoration)
* **变更点**：
  * 过去，全局的“推理详情”侧边栏（包含执行流程、推理过程、使用工具）仅在实时流式生成过程中会被更新，但在页面重载、导航返回或点击侧边栏加载对话历史时，并不会重新填充，导致侧边栏在重新打开时变成空的初始占位符。
  * **修复方案**：
    * 修改 [chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) 中的 `loadConversation(id)`。在加载历史消息并渲染完成后，提取该对话的最后一条 assistant 回复，从中解析出 `execution_steps`、`steps`（推理过程）和使用的工具列表，调用 `updateExecutionSteps`、`updateReasoning` 和 `updateTools` 重新填充全局侧边栏详情。
    * 修改 SSE completion `done` 事件处理器，确保在生成结束时也将这三个面板数据进行终态更新同步。
    * 增强 `updateReasoning(steps)` 函数以在推理步骤为空时展示规范的 placeholder 提示。

### 6. 高端交互与动效体验升级 (Premium Interactive Animations)
* **变更点**：
  * **3D 卡片旋转倾斜**：使用 `mousemove` 的客户区视区边界计算出相对于卡片中心的旋转角（最大8度），在 `chat.js` 和 `chat.css` 中增加 `.is-tilting` 控制平滑度的类，使鼠标滑动时零延迟对齐，移开时平滑回弹。
  * **拖拽磁吸 snap 上传**：通过 window 监听 dragenter/dragover 使输入胶囊高亮膨胀（`.drag-over`），通过输入框监听 dragover 激发带有虚线背景和向上微浮的 `.drag-snap` 类，增强文件拖入的重力阻尼体验。
  * **流式步骤 Accordion 手风琴式折叠**：通过 CSS 的 max-height 从 800px 转换到 0 并控制 chevron 旋转，实现推理详情卡片平滑的收起展开。当新回复的首个 token 到达时，自动收起推理详情 Timeline，防止界面高度过大。
  * **消息气泡 Staggered 级联滑入**：在 CSS 中设定 `msgEntrance` 弹簧动画（0.95 缩放到 1.0），JS 中追加 `addMessage` 索引 `idx` 并用 inline styles `--msg-index` 形式注入，使用 `animation-delay: calc(var(--msg-index, 0) * 0.08s)` 构建级联延迟滑入效果。
  * **完善度图表动态绘制与数值步进**：在 `profile.js` 中引入 `animateNumber` 动态缓动函数（采用 `easeOutExpo` 数学公式），并在加载 profile 数据时，对 svg 路径 `stroke-dasharray` 属性配置 transition 缓动触发（1.2秒，cubic-bezier），完成从 0 到指定数值的平滑拉伸绘制和数值跳变。

---

## 三、 修改文件清单及链接

下表总结了在此分支中进行修改的关键文件：

| 文件路径 | 变更说明 |
| :--- | :--- |
| [app/agents/base_agent.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/base_agent.py) | 1. 定义 `ClientDisconnectedError(BaseException)`。<br>2. 新增 `TokenStreamingHandler` 以支持流式 Token。<br>3. 在 retry block 捕获 `ClientDisconnectedError` 向上抛出，捕获 `Exception` 执行 `db.session.rollback()`。 |
| [app/agents/orchestrator.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/orchestrator.py) | 1. 在 `_execute_single_agent()` 捕获 `ClientDisconnectedError` 向上抛出，捕获 `Exception` 执行 `db.session.rollback()`。<br>2. 将 token callback 传递给子 Agent 和 `ResultMerger`。 |
| [app/services/chat_service.py](file:///d:/Opencode_workplace/ai_career_advisor/app/services/chat_service.py) | 1. 导入并使用 `ClientDisconnectedError`。<br>2. 调整 `on_step_callback` 和 `on_token_callback`，当 `task_id` 被删除时抛出该异常。<br>3. 在后台线程 `run_agent()` 中显式捕获该异常并静默退出线程。 |
| [app/static/js/chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) | 1. 引入 `activeLoadingBubble` 实现多轮对话容器隔离。<br>2. 基于 `marked.js` 重写 Markdown 解析，加入自定义代码块复制器。<br>3. 修复 Firefox 的 Agent 选择器点击事件。<br>4. 在 `beforeunload` 时触发打断逻辑，并集成自适应 textarea、智能自动滚动及流式光标。<br>5. 新增欢迎卡片 3D 倾斜逻辑 `initWelcomeCardsTilt`，新增拖拽高亮 `initDragAndDropUpload`，并在添加历史消息时向 `addMessage` 传入累加索引值。 |
| [app/static/css/chat.css](file:///d:/Opencode_workplace/ai_career_advisor/app/static/css/chat.css) | 1. 添加 `.chat-input-wrapper.disabled` 类及其禁用样式。<br>2. 新增对 Markdown 表格、标题、代码段的全局美化定义。<br>3. 调整输入框布局（`align-items: flex-end`），支持多行 Textarea 展现。<br>4. 增加流式光标 `.streaming-active` 及其闪烁动画；添加深色代码块 `.code-block-wrapper` 的全套样式。<br>5. 新增消息级联滑入动画 `msgEntrance` 以及欢迎卡片 3D 旋转透视（`perspective(600px)`）与 `.is-tilting` 状态类。 |
| [app/static/js/profile.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/profile.js) | 1. 新增 `animateNumber` 数字跳动缓动功能。<br>2. 在 `loadProfileCompletion` 中加入 `setTimeout` 延迟生效，触发 CSS transition 从而实现环形图绘制动画。 |
| [app/static/css/style.css](file:///d:/Opencode_workplace/ai_career_advisor/app/static/css/style.css) | 1. 更新 `.completion-ring .ring-fill` 的 `transition` 属性为 1.2s 的平滑 `cubic-bezier(0.16, 1, 0.3, 1)` 渐变曲线。 |
| [app/templates/base.html](file:///d:/Opencode_workplace/ai_career_advisor/app/templates/base.html) | 引入 `marked.min.js` CDN 资源。 |
| [app/templates/career/chat.html](file:///d:/Opencode_workplace/ai_career_advisor/app/templates/career/chat.html) | 1. 在 `.agent-option` 的 `onclick` 事件中，显式传递 `event` 参数以兼容火狐。<br>2. 将聊天输入框从单行 `<input>` 升级为多行 `<textarea>`。 |

---

## 四、 后续开发及维护指南

1. **新增回调时的规范**：
   * 如果后续开发中在 Agent 中增加了其他的 LLM 调用或长时间计算，并且希望它们也支持打断机制，必须要在对应的 Callback 或循环中加入 `task_id not in ChatService._sse_task_queues` 的判断，并在不满足时抛出 `ClientDisconnectedError("Client disconnected")`。
2. **数据库事务注意事项**：
   * 在编写新的工具 (Tools) 或在 Service 中访问数据库时，若有 `try...except` 结构捕获了 SQL 相关的报错，请务必执行 `db.session.rollback()`。否则后续所有的 DB 连接都将处于 invalid 状态，导致系统服务大面积抛出 `PendingRollbackError`。
3. **DOM 操作隔离规范**：
   * 前端凡是涉及流式修改、加载状态显示、动态步骤卡片更新等需要在流式期间动态变化的 UI，**一律不得**通过 `document.getElementById` 获取全局唯一 ID，必须统一使用 `activeLoadingBubble.querySelector(...)` 来寻找，确保多轮对话时各个对话框互不干扰。
