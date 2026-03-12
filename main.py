
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database import connect_db, disconnect_db, create_tables, get_pool
from fastapi import Depends
from auth import create_token, verify_token
from users import create_users_table, find_user_by_email, create_user
from auth import verify_password
from ai_chat import get_ai_response

class ChatRequest(BaseModel):
    question: str

class LoginRequest(BaseModel):
    email:    str
    password: str

class RegisterRequest(BaseModel):
    email:    str
    password: str
    name:     str

app = FastAPI(
    title="Employee Management API",
    description="FastAPI + PostgreSQL",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await connect_db()
    await create_tables()
    await create_users_table()

@app.on_event("shutdown")
async def shutdown():
    await disconnect_db()


class Employee(BaseModel):
    name:       str
    role:       str
    department: str
    salary:     float
    status:     str
    email:      str
    joined:     Optional[str] = None


# ──────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────
@app.get("/")
async def health_check():
    return {
        "status":   "healthy",
        "version":  "2.0.0",
        "database": "PostgreSQL"
    }

# ──────────────────────────────────────────────
# GET ALL EMPLOYEES
# ──────────────────────────────────────────────
@app.get("/api/employees")
async def get_all_employees(
    department: Optional[str] = None,
    status:     Optional[str] = None,
    current_user: str = Depends(verify_token)
):
    # get_pool() called at request time — always fresh!
    pool = get_pool()
    async with pool.acquire() as conn:
        query  = "SELECT * FROM employees WHERE 1=1"
        params = []

        if department:
            params.append(department)
            query += f" AND LOWER(department) = LOWER(${len(params)})"
        if status:
            params.append(status)
            query += f" AND LOWER(status) = LOWER(${len(params)})"

        query += " ORDER BY id"
        rows = await conn.fetch(query, *params)
        return {"total": len(rows), "employees": [dict(r) for r in rows]}

# ──────────────────────────────────────────────
# GET SINGLE EMPLOYEE
# ──────────────────────────────────────────────
@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM employees WHERE id = $1", employee_id
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
        return dict(row)

# ──────────────────────────────────────────────
# CREATE EMPLOYEE
# ──────────────────────────────────────────────
@app.post("/api/employees", status_code=201)
async def create_employee(employee: Employee):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO employees (name, role, department, salary, status, email, joined)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, employee.name, employee.role, employee.department,
             employee.salary, employee.status, employee.email, employee.joined)
        return {"message": "Employee created successfully", "employee": dict(row)}

# ──────────────────────────────────────────────
# UPDATE EMPLOYEE
# ──────────────────────────────────────────────
@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: int, employee: Employee):
    pool = get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT id FROM employees WHERE id = $1", employee_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

        row = await conn.fetchrow("""
            UPDATE employees SET
                name=$1, role=$2, department=$3,
                salary=$4, status=$5, email=$6, joined=$7
            WHERE id=$8 RETURNING *
        """, employee.name, employee.role, employee.department,
             employee.salary, employee.status, employee.email,
             employee.joined, employee_id)
        return {"message": "Employee updated successfully", "employee": dict(row)}

# ──────────────────────────────────────────────
# DELETE EMPLOYEE
# ──────────────────────────────────────────────
@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM employees WHERE id=$1 RETURNING name", employee_id
        )
        if not row:
            raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
        return {"message": f"Employee '{row['name']}' deleted successfully"}

# ──────────────────────────────────────────────
# GET STATS
# ──────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    pool = get_pool()
    async with pool.acquire() as conn:
        total      = await conn.fetchval("SELECT COUNT(*) FROM employees")
        active     = await conn.fetchval("SELECT COUNT(*) FROM employees WHERE status='Active'")
        avg_salary = await conn.fetchval("SELECT AVG(salary) FROM employees")
        dept_rows  = await conn.fetch("""
            SELECT department, COUNT(*) as count
            FROM employees GROUP BY department ORDER BY department
        """)
        return {
            "total_employees":      total,
            "active_employees":     active,
            "average_salary":       round(float(avg_salary or 0), 2),
            "total_departments":    len(dept_rows),
            "department_breakdown": {r["department"]: r["count"] for r in dept_rows}
        }
# ──────────────────────────────────────────────
# JWT Token Creation & Validation
# ──────────────────────────────────────────────
@app.post("/auth/login")
async def login(request: LoginRequest):
    """
    Login endpoint — returns JWT token if credentials valid.

    MuleSoft analogy:
    Like calling an OAuth2 token endpoint:
    POST /oauth2/token
    → returns { access_token: "xxx", token_type: "Bearer" }

    React will store this token and send it
    with every subsequent API request.
    """
    # Step 1: Find user by email
    user = await find_user_by_email(request.email)

    # Step 2: Check user exists AND password matches
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Step 3: Create JWT token with user info inside
    token = create_token({"sub": user["email"], "name": user["name"]})

    return {
        "access_token": token,
        "token_type":   "Bearer",
        "user": {
            "email": user["email"],
            "name":  user["name"]
        }
    }

app.post("/api/ai/chat")
async def ai_chat(
    request: ChatRequest,
    current_user: str = Depends(verify_token)
):
    try:
        response = await get_ai_response(request.question)
        return {
            "question": request.question,
            "answer":   response,
            "model":    "llama3-8b-8192"
        }
    except Exception as e:
        # This prints the EXACT error to Render logs
        print(f"AI Chat Error: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)}"   
        )
@app.post("/auth/register", status_code=201)
async def register(request: RegisterRequest):
    """
    Register a new user.
    Creates user with hashed password in PostgreSQL.
    """
    user = await create_user(request.email, request.password, request.name)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    return {
        "message": "User registered successfully",
        "user": user
    }


@app.get("/auth/me")
async def get_me(current_user: str = Depends(verify_token)):
    """
    Protected endpoint — returns current logged-in user.
    Depends(verify_token) = automatically checks JWT token!

    MuleSoft analogy:
    Like an API endpoint protected by OAuth2 policy.
    No valid token → 401 Unauthorized automatically.

    Test this in /docs — click the lock icon first!
    """
    user = await find_user_by_email(current_user)
    return {"email": user["email"], "name": user["name"]}
