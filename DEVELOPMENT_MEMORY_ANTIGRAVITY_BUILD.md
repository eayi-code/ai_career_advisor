# antigravity-build 分支开发记忆文件

该记忆文件用于记录 `antigravity-build` 分支上针对 **AI职业决策支持系统** 的所有交互细节、容灾恢复以及顶级UI/UX升级等方面的更新情况，以方便后续的迭代与开发。

---

## 一、 更新概述

在 `antigravity-build` 分支中，主要针对系统的交互体验、流式输出、数据库异常自愈以及打断（Stop）逻辑进行了重构，完成了以下关键提升：
1. **多智能体流式推理（SSE）**：打通了 LangChain 框架与前端 SSE 通信，实现了实时 Token 级别推理 and 步骤状态展示。
2. **连接打断（Stop）优雅退出**：解决了用户中途点击“停止生成”后，后端不断重试、触发降级策略并抛出大量 Traceback 报错的异常问题。
3. **多轮对话 DOM 冲突修复**：解决了在同一次对话中连续提问时，流式输出覆盖首个对话框的 Bug。
4. **SQLAlchemy 事务自愈**：修复了 Agent 重试时由于之前的 SQL 报错未回滚引发的 `PendingRollbackError`。
5. **Marked.js 精美 Markdown 渲染**：引入专业 Markdown 渲染库，完美呈现代码块、 zebra 条纹表格 and 有序/无序列表。
6. **火狐浏览器（Firefox）兼容性修复**：修复了在 Firefox 下因使用非标准 `window.event` 导致无法切换 Agent 的 Bug。
7. **全局推理弹窗数据恢复**：解决了用户切换界面返回或加载历史对话后，全局“推理详情”侧边栏内容变为空白占位符的 Bug。
8. **ChatGPT/Gemini 风格的自增长输入框 (Auto-grow Textarea)**：将单行 Input 替换为多行 Textarea，支持 Shift+Enter 换行、Enter 快捷发送，输入框高度可随输入字数自增长。
9. **智能防抖滚动定位 (Smart Autoscroll)**：流式生成过程中智能判断用户滚动位置。若用户手动向上滚动查看历史记录，则暂停强制滚屏，防止页面跳动影响阅读。
10. **流式光标与代码块一键复制**：流式生成末尾增加了脉冲打字光标；使用 `marked` 扩展了代码渲染器，实现精美的深色代码块排版、编程语言标识及一键“复制代码”功能。
11. **精致毛玻璃胶囊输入框与滚动条移除**：强制移除了输入框文本域右侧的滚动条，收紧了输入区域并进行了最大宽度限制（`768px` 居中），统一缩小了内部发送按钮、文件上传和智能体选择器的尺寸比例；基于 `backdrop-filter: blur(20px) saturate(190%)`、内发光阴影等属性，打造出极具通透感的毛玻璃视觉效果。
12. **后台任务生存与用户消息即时保存**：解决了切换对话或页面刷新时导致的后台任务流失与消息丢失。用户消息在发送时会立即写入数据库，且即便 SSE 连接因为用户切换对话而断开，服务端的 Agent 线程也会继续运行至完成，并自动将助手回复持久化到数据库中。只有当用户明确点击“停止生成”时，才会发送显式请求终止后台任务。
13. **新对话首问 Gemini 风格呼吸发光动效**：在新对话第一次提问且智能体正在思考计算时，输入框胶囊底层会自动激活一组极具科技感与通透感的 Gemini 风格马卡龙浅色系扩散呼吸光效果（由 3 组重叠、错落漂移且自动缩放的毛玻璃彩色光斑组合而成，颜色在淡蓝、浅紫和蜜桃粉之间优雅交替），随着回答开始生成或提问结束，该动画会平滑隐退消失，增强了首屏交互的视觉震撼力。
14. **五大高端前端交互动效升级**：实现了包含 3D 卡片旋转倾斜、拖拽文件磁吸 snap 上传、Accordion 折叠展开推理步骤面板、Staggered 消息气泡级联滑入，以及个人中心完善度 SVG 环图绘制与数字跳动动画，提升了系统的现代感和精致度。

---

## 二、 核心变更详解

### 1. 流式输出与打断信号重构 (SSE & Abort)
* **变更点**：
  * 定义了 `ClientDisconnectedError(BaseException)`（位于 [base_agent.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/base_agent.py)），该异常继承自 `BaseException` 级别而非 `Exception`。
  * 当用户在前端点击“停止”或关闭页面时，SSE 生成器 `generate` 的 `finally` 块触发，从而删除 `ChatService._sse_task_queues` 中的对应 `task_id`。
  * `on_step_callback` 和 `on_token_callback` 在回调执行时检查到 `task_id` 不存在，直接抛出 `ClientDisconnectedError`。
* **设计优势**：
  * 因为 `ClientDisconnectedError` 继承自 `BaseException`，它**能够穿透** LangChain 内部的 Exception 捕获机制、Agent 内部的 `try...except Exception` 重试循环以及编排器的降级逻辑，使执行线程直接中断退出。
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
* **PDF 解析自愈 (Scanned PDF OCR Fallback)**：优化了 PDF 文本提取。若 `pypdf` 标准文本提取结果为空（通常为扫描件、画册模板或加密格式），后端会自动尝试解析 PDF 内部的表单域（Fields）和注释（Annotations）；如果依旧为空，则会自动提取 PDF 页面中嵌入的图片（最多提取前 5 张），并调用大模型 Vision API 提取文字并拼接，极大地提升了 PDF 解析的成功率与鲁棒性。
* **多模态独立配置支持 (Independent Multimodal Config)**：为了方便用户节省使用成本，在系统配置中新增了 `VISION_API_KEY`、`VISION_BASE_URL` 和 `VISION_MODEL`。图片文字识别与 PDF 图片提取识别（Vision OCR）在运行时会优先加载这三项配置（如指向 OpenRouter 的免费模型）；若未配置，则自动降级复用原有的 `OPENAI_*` 通用配置（如 mimo 大模型）。这样日常聊天对话依然能够维持使用高性能的 mimo 模型，而高消耗的图片解析则能够指向免费的多模态渠道。

### 5. 全局推理弹窗数据恢复 (Side Panel Reasoning Restoration)
* **变更点**：
  * 过去，全局的“推理详情”侧边栏（包含执行流程、推理过程、使用工具）仅在实时流式生成过程中会被更新，但在页面重载、导航返回或点击侧边栏加载对话历史时，并不会重新填充，导致侧边栏在重新打开时变成空的初始占位符。
  * **修复方案**：
    * 修改 [chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) 中的 `loadConversation(id)`。在加载历史消息并渲染完成后，提取该对话的最后一条 assistant 回复，从中解析出 `execution_steps`、`steps`（推理过程）和使用的工具列表，调用 `updateExecutionSteps`、`updateReasoning` 和 `updateTools` 重新填充全局侧边栏详情。
    * 修改 SSE completion `done` 事件处理器，确保在生成结束时也将这三个面板数据进行终态更新同步。
    * 增强 `updateReasoning(steps)` 函数以在推理步骤为空时展示规范的 placeholder 提示。

### 6. 精致毛玻璃悬浮胶囊输入框与滚动条移除 (Input Floating Capsule & Scrollbar Hiding)
* **变更点**：
  * **滚动条移除**：将 textarea (`.chat-input`) 的 `overflow-y` 设为 `hidden !important` 并隐藏 webkit 滚动条，利用 JS 自动调整高度，彻底消除右侧难看的原生滚动条。
  * **毛玻璃效果 (Glassmorphism)**：为 `.chat-input-wrapper` 增加了 `rgba(255, 255, 255, 0.45)` 的高透白色背景，设置 `backdrop-filter: blur(20px) saturate(190%)`，加上内发光阴影 `inset 0 1px 0 rgba(255,255,255,0.6)`，营造极具科技感与通透感的微晶 frosted glass 特效。
  * **悬浮式免遮挡布局 (Absolute Floating Layout)**：
    * 将 `.chat-input-area` 设为 `position: absolute; bottom: 0; left: 0; right: 0;` 悬浮定位，背景设为完全透明 `transparent`，使消息流内容可滚动并穿透显示到胶囊输入框下方。
    * 对外部容器 `.chat-input-area` 设置 `pointer-events: none`（允许鼠标穿透点击其背后的消息滚动条/内容），同时对内部胶囊 `.chat-input-wrapper` 及文件预览区 `.file-preview` 恢复 `pointer-events: auto`，保障输入与点击交互正常。
    * 对消息流容器 `.chat-layout .chat-messages` 追加 `padding-bottom: 120px` 的底部安全高度，保证最底部的聊天气泡可以滚动出来，完全不被浮动输入框遮挡。
    * 对输入框主容器 `.chat-layout .chat-container` 设置 `position: relative`，以此锚定悬浮输入框的定位。
  * **背景颜色与气泡对比度调优 (Background Contrast & Bubble Enhancements)**：
    * 将整个主工作区 `.chat-layout .main-content` 的背景色由原来的 `var(--bg-primary)`（纯白色 `#ffffff`）更改为极具现代感的冷灰石瓦色 `#eef2f6`，并将 `.chat-messages` 设为 `transparent` 继承此背景。这使悬浮在最上方的白色微晶毛玻璃胶囊能完美脱颖而出，大大提升了图层层级对比度。
    * 将用户消息气泡 `.message-user .message-content` 的背景重设为纯白色 `#ffffff`，辅以超轻量阴影 `0 2px 8px rgba(0, 0, 0, 0.04)` 及极淡的描边，在冷灰底色之上营造出高雅浮动的微浮雕卡片感，视觉区分度更加清晰醒目。
  * **紧凑胶囊尺寸 (Compact Capsule Sizing)**：
    * 限制输入区域 `.chat-input-area` 最大宽度为 `768px` 并水平居中，与对话消息流宽度对齐。
    * 输入框默认高度由 `36px` 降至 `32px`。
    * 统一将内部的“发送”按钮、文件上传按钮和智能体选择按钮的高度缩小至 `28px`，使其整体比例小巧、和谐。
  * **扫描件 PDF 优化与图片上传识别 (Scanned PDF & Image Upload OCR)**：
    * **图片上传支持**：扩展了允许上传的文件格式，新增支持 `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` 格式截图。后端 `ResumeService` 会读取图片字节并调用配置好的大模型 Vision API，结合定制 Prompt 智能提取招聘岗位截图中的职责描述、任职要求等，完美满足“截图岗位信息即可自动针对性生成简历”的诉求。
    * **多模型自愈降级与诊断 (Vision Model Adaptive Fallback & Diagnostics)**：针对部分聚合接口通道（如 mimo 默认模型）没有配置多模态 Vision 节点而报错 404 的问题，进行了多模型自适应熔断重试。系统会先发起 `client.models.list()` 列出该密钥关联的所有可用模型，自动筛选含有 `vision`, `vl`, `gpt-4o` 等关键字的多模态模型并加入候选链，结合 `gpt-4o-mini`, `gpt-4o` 进行轮询重试。如果最终仍然失败，将抛出清晰的错误，并将全部可用模型列表输出在前端 Toast，方便配置诊断。
    * **PDF 解析自愈 (Scanned PDF OCR Fallback)**：优化了 PDF 文本提取。若 `pypdf` 标准文本提取结果为空（通常为扫描件、画册模板或加密格式），后端会自动尝试解析 PDF 内部的表单域（Fields）和注释（Annotations）；如果依旧为空，则会自动提取 PDF 页面中嵌入的图片（最多提取前 5 张），并调用大模型 Vision API 提取文字并拼接，极大地提升了 PDF 解析的成功率与鲁棒性。

### 7. 高端交互与动效体验升级 (Premium Interactive Animations)
* **设计细节与变更**：
  * **3D 视差卡片倾斜**：通过 `mousemove` 计算鼠标距卡片中心的相对距离，换算出 `rotateX` 与 `rotateY`（最大限制为 8 度）以及 `scale(1.02)`，通过 perspective(600px) 提供深度感。利用 JS 实时控制 `.is-tilting` 的类添加与移除，保证跟随鼠标时流畅对齐，移出时配合 cubic-bezier 实现高质感回弹。
  * **文件拖拽 snap 磁吸上传**：window 监听 `dragenter` / `dragover`，为胶囊输入框加上高亮膨胀样式（`.drag-over`），并在胶囊局部监测到 `dragover` 时，切换至带有强烈悬浮效果与虚线边框的磁吸样式（`.drag-snap`），提供物理吸引层面的视觉回馈。
  * **流式步骤手风琴折叠 (Accordion Collapse)**：优化了推理步骤面板的伸缩展示，CSS 控制 max-height 属性（0px 到 800px 转换）并实现折叠图标 -90 度旋转。流式输出首个 token 吐出时，会自动收拢推理详情面板，降低视觉高度负荷。
  * **气泡级联 Staggered 滑入**：重构了消息气泡滑入效果，设计了 `msgEntrance` 关键帧动画。借助 CSS 变量 `var(--msg-index)`，为每个气泡动态应用 `animation-delay: calc(var(--msg-index, 0) * 0.08s)`，使历史记录或新增气泡以递增的延迟、配合 spring 弹性曲线自底向上逐个滑入。
  * **环形统计绘制与数字倍速递增**：在用户档案页面加载时，利用 `animateNumber` 动态缓动逻辑（`easeOutExpo`）让完善度数字在 1.2 秒内从 0 渐进累加到目标数值，同时将 SVG 路径的 `stroke-dasharray` 属性施加 CSS 过渡，实现环状图的圆滑伸展拉伸动画。

---

## 三、 修改文件清单及链接

下表总结了在此分支中进行修改的关键文件：

| 文件路径 | 变更说明 |
| :--- | :--- |
| [app/config.py](file:///d:/Opencode_workplace/ai_career_advisor/app/config.py) | 新增 `VISION_API_KEY`、`VISION_BASE_URL` 和 `VISION_MODEL` 变量定义，支持从环境变量加载，并自动 fallback 到标准 `OPENAI_*` 变量。 |
| [.env](file:///d:/Opencode_workplace/ai_career_advisor/.env) | 新增多模态专用模型配置模板，引导用户进行 OpenRouter 等渠道的免费模型分离配置。 |
| [app/routes/api.py](file:///d:/Opencode_workplace/ai_career_advisor/app/routes/api.py) | 新增 `/api/agent/task/abort/<task_id>` 接口以支持显式终止后台任务。 |
| [app/services/chat_service.py](file:///d:/Opencode_workplace/ai_career_advisor/app/services/chat_service.py) | 重构 `process_stream_chat` 流式对话，支持用户消息即时提前保存入库、后台线程连接断开后继续执行完毕保存，以及提供了 `abort_task` 接口实现精准的用户显式中止控制。 |
| [app/agents/base_agent.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/base_agent.py) | 1. 定义 `ClientDisconnectedError(BaseException)`。<br>2. 新增 `TokenStreamingHandler` 以支持流式 Token。<br>3. 在 retry block 捕获 `ClientDisconnectedError` 向上抛出，捕获 `Exception` 执行 `db.session.rollback()`。 |
| [app/agents/orchestrator.py](file:///d:/Opencode_workplace/ai_career_advisor/app/agents/orchestrator.py) | 1. 在 `_execute_single_agent()` 捕获 `ClientDisconnectedError` 向上抛出，捕获 `Exception` 执行 `db.session.rollback()`。<br>2. 将 token callback 传递给子 Agent 和 `ResultMerger`。 |
| [app/services/resume_service.py](file:///d:/Opencode_workplace/ai_career_advisor/app/services/resume_service.py) | 1. 扩展 `upload_resume` 接口，新增支持图片格式上传。<br>2. 优化 PDF 解析：结合表单域（Fields）和注释（Annotations）提取；增加扫描件 PDF 降级，提取内嵌图片并调用大模型 Vision 接口（OCR）进行文本识别。<br>3. 封装 `_extract_text_from_image_bytes` 以使用 OpenAI 多模态 Vision 接口，并优先加载 `VISION_*` 专属配置。 |
| [app/static/js/chat.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/chat.js) | 1. 引入 `activeLoadingBubble` 实现多轮对话容器隔离。<br>2. 基于 `marked.js` 自定义代码块渲染及复制代码功能。<br>3. 修复 Firefox 的 Agent 选择器点击事件（通过显式传递 `event`）。<br>4. 在 `beforeunload` 时触发打断逻辑；在 `stopProcessing` 时显式向后端发起中止 `currentTaskId` 请求。<br>5. 绑定 Textarea 自动增长及 Enter/Shift+Enter 发送换行逻辑，将默认高度调优为 `32px`。<br>6. 实现智能防抖滚动 `smartScrollToBottom`。<br>7. 加载历史对话时，提取最后一条 AI 消息重新填装全局侧边栏详情。<br>8. 扩展 `allowedExts` 以支持图片格式上传，并根据上传格式调整 Toast 解析提示。<br>9. 在流式开始时捕获 `data.task_id`，以支持精准的任务手动中止。<br>10. 新增 `isNewConversation` 全局状态控制，配合 `initChatPage` 和 `loadConversation` 自动判断新对话首问并触发扩散光动效。<br>11. 新增欢迎卡片 3D 旋转交互逻辑 `initWelcomeCardsTilt`，新增文件拖曳高亮 `initDragAndDropUpload`，并在添加消息气泡时将累加的索引值传递入 `addMessage` 中。 |
| [app/static/css/chat.css](file:///d:/Opencode_workplace/ai_career_advisor/app/static/css/chat.css) | 1. 添加 `.chat-input-wrapper.disabled` 样式。<br>2. 新增对 Markdown 表格、标题、代码段的精细样式定义。<br>3. 编写深色代码块 `.code-block-wrapper`、工具条及一键复制视觉规则。<br>4. 实现流式打字光标闪烁动画。<br>5. 重构输入框区域，隐藏 textarea 滚动条，并在输入区域 and 胶囊引入毛玻璃 and 768px 限制，缩小内部按钮尺寸以支持精致感胶囊。<br>6. 编写 `.input-glow-glow` 以及三组 `.glow-bubble` 的微晶马卡龙浅色系扩散呼吸发光背景样式与运动关键帧；更新 `.chat-input-wrapper` 包含 relative 定位与 z-index: 2 控制以防图层遮挡。<br>7. 编写 `msgEntrance` 消息级联滑入动画、透视效果（`perspective`）及用于 3D 卡片控制平滑性的 `.is-tilting` 控制类。 |
| [app/static/js/profile.js](file:///d:/Opencode_workplace/ai_career_advisor/app/static/js/profile.js) | 1. 新增 `animateNumber` 数字跳动缓动功能。<br>2. 在 `loadProfileCompletion` 中加入 `setTimeout` 延迟生效，触发 CSS transition 从而实现环形图绘制动画。 |
| [app/static/css/style.css](file:///d:/Opencode_workplace/ai_career_advisor/app/static/css/style.css) | 1. 更新 `.completion-ring .ring-fill` 的 `transition` 属性为 1.2s 的平滑 `cubic-bezier(0.16, 1, 0.3, 1)` 渐变曲线。 |
| [app/templates/base.html](file:///d:/Opencode_workplace/ai_career_advisor/app/templates/base.html) | 引入 `marked.min.js` CDN 资源。 |
| [app/templates/career/chat.html](file:///d:/Opencode_workplace/ai_career_advisor/app/templates/career/chat.html) | 1. 将聊天输入框元素替换为 `<textarea>`，支持多行文本。<br>2. 在 `.agent-option` 的 `onclick` 事件中，显式传递 `event` 参数以兼容火狐。<br>3. 扩展上传 input 的 `accept` 属性以允许图片格式。<br>4. 嵌入 `inputGlow` 扩散光底层动效节点结构。 |

---

## 四、 后续开发及维护指南

1. **新增回调时的规范**：
   * 如果后续开发中在 Agent 中增加了其他的 LLM 调用或长时间计算，并且希望它们也支持打断机制，必须要在对应的 Callback 或循环中加入 `task_id not in ChatService._sse_task_queues` 的判断，并在不满足时抛出 `ClientDisconnectedError("Client disconnected")`。
2. **数据库事务注意事项**：
   * 在编写新的工具 (Tools) 或在 Service 中访问数据库时，若有 `try...except` 结构捕获了 SQL 相关的报错，请务必执行 `db.session.rollback()`。否则后续所有的 DB 连接都将处于 invalid 状态，导致系统服务大面积抛出 `PendingRollbackError`。
3. **DOM 操作隔离规范**：
   * 前端凡是涉及流式修改、加载状态显示、动态步骤卡片更新等需要在流式期间动态变化的 UI，**一律不得**通过 `document.getElementById` 获取全局唯一 ID，必须统一使用 `activeLoadingBubble.querySelector(...)` 来寻找，确保多轮对话时各个对话框互不干扰。
