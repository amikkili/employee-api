from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# ──────────────────────────────────────────────
# APP SETUP
# Think of this like your MuleSoft API spec —
# this defines your entire API in one place
# ──────────────────────────────────────────────
app = FastAPI(
    title="Employee Management DashBoard",
    description="FastAPI backend for Employee Management System",
    version="1.0.0"
)

# ──────────────────────────────────────────────
# CORS MIDDLEWARE
# This allows your React app to call this API
# Without this → browser blocks all requests!
# MuleSoft analogy: like allowing HTTP calls
# from external systems in your API policy
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # In production: add your Render URL here
    allow_credentials=True,
    allow_methods=["*"],        # Allow GET, POST, PUT, DELETE
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# DATA MODEL (Schema)
# Like your DataWeave schema / JSON structure
# Pydantic validates every request automatically!
# ──────────────────────────────────────────────
class Employee(BaseModel):
    id: Optional[int] = None
    name: str
    role: str
    department: str
    salary: float
    status: str
    email: str
    joined: str

# ──────────────────────────────────────────────
# IN-MEMORY DATABASE
# Like a flow variable storing your payload
# Simple list — we'll upgrade to PostgreSQL later
# ──────────────────────────────────────────────
employees_db = [
    {"id": 1, "name": "Sarah Mitchell",  "role": "Senior Developer",   "department": "Engineering", "salary": 85000, "status": "Active",   "email": "sarah@company.com",  "joined": "2020-03-15"},
    {"id": 2, "name": "James Okafor",    "role": "MuleSoft Architect",  "department": "Integration", "salary": 95000, "status": "Active",   "email": "james@company.com",  "joined": "2019-07-22"},
    {"id": 3, "name": "Priya Sharma",    "role": "Data Analyst",        "department": "Analytics",   "salary": 72000, "status": "Active",   "email": "priya@company.com",  "joined": "2021-01-10"},
    {"id": 4, "name": "Tom Henderson",   "role": "Product Manager",     "department": "Product",     "salary": 90000, "status": "On Leave", "email": "tom@company.com",    "joined": "2018-11-05"},
    {"id": 5, "name": "Aisha Patel",     "role": "UX Designer",         "department": "Design",      "salary": 78000, "status": "Active",   "email": "aisha@company.com",  "joined": "2022-04-18"},
    {"id": 6, "name": "Carlos Mendez",   "role": "DevOps Engineer",     "department": "Engineering", "salary": 88000, "status": "Active",   "email": "carlos@company.com", "joined": "2020-09-01"},
]

# Auto-increment ID counter
next_id = 7


# ══════════════════════════════════════════════
# API ENDPOINTS (Your MuleSoft Flow equivalents)
# ══════════════════════════════════════════════

# ──────────────────────────────────────────────
# HEALTH CHECK
# Always have this — Render uses it to verify
# your service is running (like MuleSoft /ping)
# ──────────────────────────────────────────────
@app.get("/")
def health_check():
    return {
        "status": "healthy",
        "service": "Employee Management API",
        "version": "1.0.0"
    }

# ──────────────────────────────────────────────
# GET ALL EMPLOYEES
# MuleSoft equivalent:
#   GET /api/employees → Database SELECT → Transform → Return JSON
# ──────────────────────────────────────────────
@app.get("/api/employees")
def get_all_employees(department: Optional[str] = None, status: Optional[str] = None):
    """
    Get all employees.
    Optional filters: ?department=Engineering or ?status=Active
    """
    result = employees_db.copy()

    # Filter by department if provided (like DataWeave filter)
    if department:
        result = [e for e in result if e["department"].lower() == department.lower()]

    # Filter by status if provided
    if status:
        result = [e for e in result if e["status"].lower() == status.lower()]

    return {
        "total": len(result),
        "employees": result
    }

# ──────────────────────────────────────────────
# GET SINGLE EMPLOYEE BY ID
# MuleSoft equivalent:
#   GET /api/employees/{id} → Find by ID → Return or 404
# ──────────────────────────────────────────────
@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: int):
    """Get a single employee by ID"""

    # Find employee (like DataWeave filter with single result)
    employee = next((e for e in employees_db if e["id"] == employee_id), None)

    if not employee:
        # Like MuleSoft On-Error → raise HTTP 404
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    return employee

# ──────────────────────────────────────────────
# CREATE NEW EMPLOYEE
# MuleSoft equivalent:
#   POST /api/employees → Validate → Insert → Return created
# ──────────────────────────────────────────────
@app.post("/api/employees", status_code=201)
def create_employee(employee: Employee):
    """Create a new employee"""
    global next_id

    # Build new employee object
    new_employee = employee.dict()
    new_employee["id"] = next_id
    next_id += 1

    # Add to our in-memory DB
    employees_db.append(new_employee)

    return {
        "message": "Employee created successfully",
        "employee": new_employee
    }

# ──────────────────────────────────────────────
# UPDATE EMPLOYEE
# MuleSoft equivalent:
#   PUT /api/employees/{id} → Find → Update fields → Return updated
# ──────────────────────────────────────────────
@app.put("/api/employees/{employee_id}")
def update_employee(employee_id: int, updated: Employee):
    """Update an existing employee"""

    # Find index of employee
    index = next((i for i, e in enumerate(employees_db) if e["id"] == employee_id), None)

    if index is None:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    # Update employee (keep same ID)
    updated_employee = updated.dict()
    updated_employee["id"] = employee_id
    employees_db[index] = updated_employee

    return {
        "message": "Employee updated successfully",
        "employee": updated_employee
    }

# ──────────────────────────────────────────────
# DELETE EMPLOYEE
# MuleSoft equivalent:
#   DELETE /api/employees/{id} → Find → Remove → Return confirmation
# ──────────────────────────────────────────────
@app.delete("/api/employees/{employee_id}")
def delete_employee(employee_id: int):
    """Delete an employee"""

    # Find employee first
    employee = next((e for e in employees_db if e["id"] == employee_id), None)

    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    # Remove from list
    employees_db.remove(employee)

    return {
        "message": f"Employee '{employee['name']}' deleted successfully"
    }

# ──────────────────────────────────────────────
# GET STATS (Bonus endpoint — powers your dashboard)
# ──────────────────────────────────────────────
@app.get("/api/stats")
def get_stats():
    """Get dashboard statistics"""

    total = len(employees_db)
    active = len([e for e in employees_db if e["status"] == "Active"])
    avg_salary = sum(e["salary"] for e in employees_db) / total if total else 0
    departments = len(set(e["department"] for e in employees_db))

    return {
        "total_employees": total,
        "active_employees": active,
        "average_salary": round(avg_salary, 2),
        "total_departments": departments,
        "department_breakdown": {
            dept: len([e for e in employees_db if e["department"] == dept])
            for dept in set(e["department"] for e in employees_db)
        }
    }


# ──────────────────────────────────────────────
# RUN SERVER (for local development)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)