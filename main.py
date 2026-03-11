from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database import connect_db, disconnect_db, create_tables, db_pool

# ──────────────────────────────────────────────
# APP SETUP
# ──────────────────────────────────────────────
app = FastAPI(
    title="Employee Management API",
    description="FastAPI + PostgreSQL backend for Employee Management System",
    version="2.0.0"
)

# ──────────────────────────────────────────────
# CORS — Allow React frontend to call this API
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# STARTUP & SHUTDOWN
@app.on_event("startup")
async def startup():
    await connect_db()    # Connect to PostgreSQL
    await create_tables() # Create tables if not exist

@app.on_event("shutdown")
async def shutdown():
    await disconnect_db() # Clean disconnect


# ──────────────────────────────────────────────
# DATA MODEL
# Pydantic validates every incoming request

class Employee(BaseModel):
    name:       str
    role:       str
    department: str
    salary:     float
    status:     str
    email:      str
    joined:     Optional[str] = None


# ══════════════════════════════════════════════
# API ENDPOINTS
# ══════════════════════════════════════════════

# ──────────────────────────────────────────────
# HEALTH CHECK
# ──────────────────────────────────────────────
@app.get("/")
async def health_check():
    return {
        "status":  "healthy",
        "service": "Employee Management API",
        "version": "2.0.0",
        "database": "PostgreSQL"
    }

# ──────────────────────────────────────────────
# GET ALL EMPLOYEES
# SQL: SELECT * FROM employees
# ──────────────────────────────────────────────
@app.get("/api/employees")
async def get_all_employees(
    department: Optional[str] = None,
    status:     Optional[str] = None
):
    async with db_pool.acquire() as conn:

        # Build query dynamically based on filters
        # Like DataWeave building dynamic WHERE clause
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

        # Convert rows to list of dicts
        employees = [dict(row) for row in rows]

        return {
            "total":     len(employees),
            "employees": employees
        }

# ──────────────────────────────────────────────
# GET SINGLE EMPLOYEE
# SQL: SELECT * FROM employees WHERE id = $1
# ──────────────────────────────────────────────
@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM employees WHERE id = $1",
            employee_id
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Employee {employee_id} not found"
            )
        return dict(row)

# ──────────────────────────────────────────────
# CREATE EMPLOYEE
# SQL: INSERT INTO employees ... RETURNING *
# MuleSoft: Database INSERT operation
# ──────────────────────────────────────────────
@app.post("/api/employees", status_code=201)
async def create_employee(employee: Employee):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO employees
                (name, role, department, salary, status, email, joined)
            VALUES
                ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """,
            employee.name,
            employee.role,
            employee.department,
            employee.salary,
            employee.status,
            employee.email,
            employee.joined
        )
        return {
            "message":  "Employee created successfully",
            "employee": dict(row)
        }

# ──────────────────────────────────────────────
# UPDATE EMPLOYEE
# SQL: UPDATE employees SET ... WHERE id = $1
# MuleSoft: Database UPDATE operation
# ──────────────────────────────────────────────
@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: int, employee: Employee):
    async with db_pool.acquire() as conn:

        # Check exists first
        exists = await conn.fetchval(
            "SELECT id FROM employees WHERE id = $1",
            employee_id
        )
        if not exists:
            raise HTTPException(
                status_code=404,
                detail=f"Employee {employee_id} not found"
            )

        row = await conn.fetchrow("""
            UPDATE employees SET
                name       = $1,
                role       = $2,
                department = $3,
                salary     = $4,
                status     = $5,
                email      = $6,
                joined     = $7
            WHERE id = $8
            RETURNING *
        """,
            employee.name,
            employee.role,
            employee.department,
            employee.salary,
            employee.status,
            employee.email,
            employee.joined,
            employee_id
        )
        return {
            "message":  "Employee updated successfully",
            "employee": dict(row)
        }

# ──────────────────────────────────────────────
# DELETE EMPLOYEE
# SQL: DELETE FROM employees WHERE id = $1
# ──────────────────────────────────────────────
@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM employees WHERE id = $1 RETURNING name",
            employee_id
        )
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Employee {employee_id} not found"
            )
        return {
            "message": f"Employee '{row['name']}' deleted successfully"
        }

# ──────────────────────────────────────────────
# GET STATS
# SQL: Multiple aggregation queries
# ──────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats():
    async with db_pool.acquire() as conn:

        # Run all stat queries in parallel
        total      = await conn.fetchval("SELECT COUNT(*) FROM employees")
        active     = await conn.fetchval("SELECT COUNT(*) FROM employees WHERE status = 'Active'")
        avg_salary = await conn.fetchval("SELECT AVG(salary) FROM employees")

        # Department breakdown
        dept_rows  = await conn.fetch("""
            SELECT department, COUNT(*) as count
            FROM employees
            GROUP BY department
            ORDER BY department
        """)

        return {
            "total_employees":      total,
            "active_employees":     active,
            "average_salary":       round(float(avg_salary or 0), 2),
            "total_departments":    len(dept_rows),
            "department_breakdown": {
                row["department"]: row["count"]
                for row in dept_rows
            }
        }