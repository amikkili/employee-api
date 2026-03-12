import os
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from database import get_pool

async def get_ai_response(question: str) -> str:

    # Step 1: Fetch real data from YOUR PostgreSQL
    pool = get_pool()
    async with pool.acquire() as conn:
        employees = await conn.fetch("SELECT * FROM employees ORDER BY id")
        emp_list  = [dict(e) for e in employees]

    # Step 2: Format data as context for the AI
    context = "Here is the current employee data:\n\n"
    for e in emp_list:
        context += (
            f"- {e['name']} | {e['role']} | {e['department']} "
            f"| ${e['salary']:,.0f} | {e['status']}\n"
        )

    # Step 3: Build the prompt
    # System message = AI's personality + rules
    # Human message  = the actual user question
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",        # cost-effective model
        temperature=0.3,               # lower = more factual
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

    messages = [
        SystemMessage(content=f"""
            You are an intelligent HR assistant for WorkFlow HR system.
            Answer questions about employees using ONLY the data provided.
            Be concise, professional, and helpful.
            Format numbers with $ and commas.
            If asked something outside the data, say you don't have that info.

            {context}
        """),
        HumanMessage(content=question)
    ]

    # Step 4: Call OpenAI and return response
    response = await llm.ainvoke(messages)
    return response.content
