import sqlite3
from pathlib import Path

DB_PATH = Path("attendance_payroll.db")

def create_tables(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # Employees
    c.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        role TEXT,
        department TEXT,
        hourly_rate REAL NOT NULL,
        contact TEXT,
        active INTEGER DEFAULT 1
    )
    """)
    # Attendance
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        event TEXT NOT NULL CHECK(event IN ('sign_in','sign_out','correction')),
        timestamp TEXT NOT NULL,
        corrected_by_hr INTEGER DEFAULT 0,
        note TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )
    """)
    # Payroll adjustments (allowances/deductions) per month
    c.execute("""
    CREATE TABLE IF NOT EXISTS adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        description TEXT,
        amount REAL NOT NULL, -- positive for allowance, negative for deduction
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )
    """)
    # Payroll records (one per employee per month)
    c.execute("""
    CREATE TABLE IF NOT EXISTS payroll_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        regular_hours REAL,
        overtime_hours REAL,
        hourly_rate REAL,
        gross_pay REAL,
        total_adjustments REAL,
        net_pay REAL,
        generated_at TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(id)
    )
    """)
    conn.commit()
    conn.close()
    print(f"Database created / verified at {db_path}")

if __name__ == "__main__":
    create_tables()
