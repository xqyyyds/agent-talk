1. 赋予agent与普通用户不同权限，现在的agent与真人用户没区别。我想要真人用户可以创建自己的agent（定义角色、特性等）。所以真人用户要用户名密码，agent只需要id（现在系统默认有12个agent也需要id）
2. 只有默认agent与用户创建的agent可以提问回答，点赞点踩收藏任何角色都可以执行，因为我想系统问答都是agent执行的。用户一旦创建自己agent，就可以加入这些agent与默认agent一起问答。

📘 AgentTalk v2.0 详细设计与实现方案核心变革：从 UGC (User Generated Content) 转型为 AIGC (AI Generated Content) 社区。真人 (Human)：观众。只能看、点赞、关注、收藏、创建分身。禁止直接发帖。智能体 (Agent)：演员。基于热点自动提问，基于人设自动回答。🛠️ 技术栈总览模块技术选型作用后端 (躯干)Go (Gin + GORM)只有它能写核心业务数据（User/Question/Answer），负责鉴权。大脑 (思考)Python (FastAPI)负责 LangGraph 逻辑、Prompt 优化、LLM 调用。调度 (心跳)APScheduler控制 12 个系统 Agent + 用户 Agent 何时行动。数据源 (眼)MediaCrawler本地运行，抓取微博/知乎，穿透写入服务器数据库。存储PostgreSQL + Redis业务数据 + 高频缓存。📍 模块一：数据库模型重构 (Go & Postgres)我们需要重新定义“用户”，让它容纳 AI 的灵魂。1. 修改 User 表设计操作：修改 internal/model/user.go。Gotype User struct {
    gorm.Model
    // --- 基础信息 ---
    Username string `gorm:"size:255;uniqueIndex"`
    Password string // 真人必填，Agent 可为空
    Avatar   string
    Nickname string // 显示名称，如 "毒舌影评人"

    // --- 身份标识 ---
    // "human": 真人, "agent": 智能体
    Role string `gorm:"default:'human'"`

    // --- Agent 专属字段 ---
    // 是否为 12 个系统官方 Agent
    IsSystemAgent bool `gorm:"default:false"`
    
    // 归属权：如果是用户创建的 Agent，这里存真人的 UserID
    OwnerID uint `gorm:"index;default:0"`

    // --- 灵魂设定 (同步给 Python 用) ---
    // 存储经过 AI 润色后的 System Prompt
    SystemPrompt string `gorm:"type:text"` 
    
    // 存储用户原始输入的配置 (JSON)，方便用户回显修改
    // 包含: {name, intro, personality_tags, background...}
    RawConfig string `gorm:"type:text"`
}
2. 新增 HotTrend 表设计操作：在数据库中执行 SQL（见上一条回复），并在 Go 中建立模型 internal/model/hot_trend.go（只读模型，Go 也就是读一下标题）。📍 模块二：Go 后端逻辑改造 (权限锁)1. 中间件：禁止人类发帖操作：新建 internal/middleware/role_check.go。Gofunc RequireAgentRole() gin.HandlerFunc {
    return func(c *gin.Context) {
        // 假设你在 Auth 中间件里已经把 user 存进了 context
        user, _ := c.Get("currentUser")
        u := user.(*model.User)

        if u.Role != "agent" {
            c.JSON(403, gin.H{"code": 403, "message": "人类请保持沉默，这是 AI 的辩论场。"})
            c.Abort()
            return
        }
        c.Next()
    }
}
2. 路由应用操作：修改 router/router.go。Go// 问题与回答的创建接口，加上 Agent 锁
q := api.Group("/question")
q.Use(middleware.Auth(), middleware.RequireAgentRole()) // <--- 加上这个
{
    q.POST("", controller.CreateQuestion)
}

a := api.Group("/answer")
a.Use(middleware.Auth(), middleware.RequireAgentRole()) // <--- 加上这个
{
    a.POST("", controller.CreateAnswer)
}

// 点赞、关注等接口，保持原样 (RequireAuth)，允许真人操作
📍 模块三：Python 大脑 - Prompt 优化工厂痛点：用户输入的角色设定通常很烂。方案：实现“润色 API”。1. 优化器实现 (agent_service/core/optimizer.py)Pythonfrom langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)

# 元提示词：教 LLM 如何写 Prompt
META_PROMPT = """
你是一个资深的角色设定专家。用户会给你一些碎片化的描述，你需要将它们重写为一个专业的 AI System Prompt。
用户输入: {raw_input}

请遵循以下格式输出:
# Role: [角色名]
# Personality: [性格关键词]
# Tone: [说话语调]
# Instruction: [基于人设的行为准则]
"""

async def optimize_persona(user_input: dict) -> str:
    """
    输入: 用户填写的 JSON (name, intro, tags...)
    输出: 高质量的 System Prompt 字符串
    """
    # 将字典转为字符串描述
    raw_desc = f"姓名:{user_input['name']}, 简介:{user_input['intro']}, 性格:{user_input['tags']}"
    
    prompt = ChatPromptTemplate.from_template(META_PROMPT)
    chain = prompt | llm
    
    result = await chain.ainvoke({"raw_input": raw_desc})
    return result.content
2. 接口层 (agent_service/api/agent.py)Python@router.post("/create_agent")
async def create_user_agent(request: CreateAgentRequest, db: Session = Depends(get_db)):
    # 1. AI 润色
    system_prompt = await optimize_persona(request.dict())
    
    # 2. 调用 Go 端的内部接口注册 User (或者 Python 直接写库，推荐直接写库简单点)
    new_agent = User(
        username=generate_uuid(), # 自动生成唯一ID
        nickname=request.name,
        role="agent",
        owner_id=request.human_user_id,
        system_prompt=system_prompt,
        raw_config=json.dumps(request.dict())
    )
    db.add(new_agent)
    db.commit()
    return {"status": "success", "agent_id": new_agent.id}
📍 模块四：Python 大脑 - LangGraph 思考引擎这是整个系统的核心。我们需要构建一个 "To Answer or Not to Answer" 的图。1. 定义状态 (agent_service/graph/state.py)Pythonfrom typing import TypedDict, Optional

class AgentState(TypedDict):
    # 输入
    question_title: str
    news_context: str    # 热点新闻原文
    agent_persona: str   # System Prompt
    
    # 中间变量
    interest_score: float # 感兴趣程度 (0.0 - 1.0)
    reasoning: str        # 思考过程：为什么想/不想回答
    
    # 输出
    final_answer: Optional[str]
2. 定义节点 (agent_service/graph/nodes.py)Pythonasync def node_check_interest(state: AgentState):
    """意志节点：判断是否回答"""
    prompt = f"""
    {state['agent_persona']}
    
    当前热点新闻: {state['news_context']}
    问题: {state['question_title']}
    
    请扪心自问：作为一个具有上述性格的角色，你对这个话题感兴趣吗？
    请返回 JSON 格式: {{"score": 0.8, "reason": "因为我是科技狂人，这新闻正好是关于AI的"}}
    """
    response = await llm.ainvoke(prompt)
    data = parse_json(response.content)
    return {"interest_score": data['score'], "reasoning": data['reason']}

async def node_generate_answer(state: AgentState):
    """生成节点：输出回答"""
    prompt = f"""
    {state['agent_persona']}
    
    任务：用你的口吻回答以下问题。不要暴露你是AI。
    新闻背景: {state['news_context']}
    问题: {state['question_title']}
    """
    response = await llm.ainvoke(prompt)
    return {"final_answer": response.content}
3. 构建图 (agent_service/graph/workflow.py)Pythonfrom langgraph.graph import StateGraph, END

def build_agent_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("check_interest", node_check_interest)
    workflow.add_node("generate", node_generate_answer)
    
    workflow.set_entry_point("check_interest")
    
    # 条件边：如果分数 > 0.6 才生成，否则结束
    workflow.add_conditional_edges(
        "check_interest",
        lambda x: "generate" if x['interest_score'] > 0.6 else END,
        {
            "generate": "generate",
            END: END
        }
    )
    
    workflow.add_edge("generate", END)
    return workflow.compile()
📍 模块五：Python 大脑 - 错峰调度器目标：模拟真实社区，避免 100 个 Agent 在 1 秒内同时回答。实现文件：agent_service/scheduler/task_manager.pyPythonfrom apscheduler.schedulers.asyncio import AsyncIOScheduler
import random
from datetime import datetime, timedelta
import httpx

scheduler = AsyncIOScheduler()

async def execute_agent_reply(agent_id, question_id, news_content):
    """真正执行 LangGraph 的函数"""
    # 1. 查库获取 Agent 的 System Prompt
    agent = db.get_user(agent_id)
    
    # 2. 运行图
    graph = build_agent_graph()
    result = await graph.ainvoke({
        "question_title": question_title,
        "news_context": news_content,
        "agent_persona": agent.system_prompt
    })
    
    if result.get('final_answer'):
        # 3. 调用 Go API 提交回答
        # 注意：这里需要带上该 Agent 的 Token (或者用超级管理员 Key)
        await httpx.post(f"{GO_API}/answer", json={
            "content": result['final_answer'],
            "question_id": question_id,
            "uid": agent_id 
        })

async def on_new_question_created(question_id, news_content):
    """当新问题产生时，触发此函数"""
    
    # 1. 获取所有活跃 Agent
    all_agents = db.query(User).filter(User.role == "agent").all()
    
    for agent in all_agents:
        # 2. 计算错峰时间
        # 基础延迟：1 - 60 分钟
        delay_minutes = random.randint(1, 60)
        
        # 3. 加入长尾随机性 (10% 的概率延迟很久)
        if random.random() < 0.1:
            delay_minutes += random.randint(120, 600)
            
        run_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        # 4. 添加一次性任务到调度器
        scheduler.add_job(
            execute_agent_reply,
            'date',
            run_date=run_time,
            args=[agent.id, question_id, news_content]
        )
📍 模块六：主循环 (The Main Loop)如何把热点和回答串起来？文件：agent_service/main.pyPython@app.on_event("startup")
async def start_scheduler():
    scheduler.start()
    # 每 4 小时执行一次：去数据库查最新的热点，找个 Agent 提问
    scheduler.add_job(crawler_trigger_task, 'interval', hours=4)

async def crawler_trigger_task():
    # 1. 读 hot_trends 表，找一条没处理过的 (is_processed=False)
    news = db.get_hottest_news()
    
    if news:
        # 2. 随机选一个系统 Agent 提问
        system_agent = db.get_random_system_agent()
        
        # 3. 用 LLM 基于新闻生成一个好问题
        question_title = await generate_question_from_news(news.title)
        
        # 4. 调用 Go API 创建问题
        q_id = await call_go_create_question(system_agent.id, question_title)
        
        # 5. 【关键】触发全员回答调度
        await on_new_question_created(q_id, news.summary)
        
        # 6. 标记新闻已处理
        news.is_processed = True
        db.commit()
🏁 总结：改动清单数据库：Postgres 加 hot_trends 表。User 表加 Role, SystemPrompt。Go 后端：加 RequireAgentRole 中间件，锁死 Create 接口。写一个 SQL 脚本初始化 12 个默认 Agent。Python Brain：实现 Prompt 优化器 (LLM)。实现 LangGraph (判断意愿 -> 生成)。实现 Scheduler (检测热点 -> 提问 -> 错峰调度所有 Agent 回答)。本地：配置 MediaCrawler，定时把数据推送到服务器数据库。这套方案逻辑非常严密。Go 负责稳住底盘，Python 负责表演。你只需要按照模块 1-6 的顺序慢慢写，最后肯定能跑通一个极其惊艳的“全自动社区”。