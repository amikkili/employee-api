import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage   # ✅ correct import path
from database import get_pool


async def get_ai_response(question: str) -> str:
    """
    AI HR Assistant — answers questions about YOUR employee data.

    Flow:
    1. Fetch all employees from PostgreSQL
    2. Format as context string for the AI
    3. Send context + question to Groq (Llama3)
    4. Return AI's natural language answer

    MuleSoft analogy:
    Like a flow: DB Connector → DataWeave → AI Connector → Return
    """

    # ── Step 1: Fetch real data from PostgreSQL ──
    pool = get_pool()
    async with pool.acquire() as conn:
        employees = await conn.fetch("SELECT * FROM employees ORDER BY id")
        emp_list  = [dict(e) for e in employees]

    # ── Step 2: Format data as AI context ────────
    context = f"Total employees: {len(emp_list)}\n\n"
    context += "Employee list:\n"
    for e in emp_list:
        context += (
            f"- Name: {e['name']} | Role: {e['role']} | "
            f"Department: {e['department']} | "
            f"Salary: ${float(e['salary']):,.0f} | "
            f"Status: {e['status']} | "
            f"Email: {e['email']}\n"
        )

    # ── Step 3: Initialize Groq LLM ──────────────
    llm = ChatGroq(
        model="llama3-8b-8192",
        temperature=0.3,
        groq_api_key=os.getenv("GROQ_API_KEY")
    )

    # ── Step 4: Build messages and call AI ────────
    messages = [
        SystemMessage(content=f"""
You are an intelligent HR assistant for WorkFlow HR Management System.
Your job is to answer questions about employees using ONLY the data below.

Rules:
- Be concise and professional
- Format salaries with $ and commas (e.g. $85,000)
- If asked something not in the data, say "I don't have that information"
- Never make up data that isn't in the employee list

{context}
        """),
        HumanMessage(content=question)
    ]

    response = await llm.ainvoke(messages)
    return response.content
