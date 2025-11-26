from typing import Optional
from datetime import datetime

from models.database import Database
from models.user import UserModel

class EmployeesController:
    def __init__(self, db, view, current_user=None):
        self.db = db
        self.view = view
        self.current_user = current_user
        self.user_model = UserModel(self.db)

    def _check_admin(self):
        """Raise error if not admin."""
        if not getattr(self.current_user, "is_hr", False):
            raise PermissionError("Only admins can access employee management")

    # --- Data operations ---
    def add_employee(self, full_name: str, role: str, department: str, contact: str, rate: float, username: str = None, password: str = None) -> int:
        self._check_admin()
        cur = self.db.execute(
            "INSERT INTO employees (full_name, role, department, contact, rate, active, created_at) VALUES (?, ?, ?, ?, ?, 1, ?)",
            (full_name, role, department, contact, float(rate), datetime.now().isoformat())
        )
        employee_id = cur.lastrowid
        
        # Create user credentials if provided
        if username and password:
            try:
                self.user_model.create_user(username, password, is_hr=False, employee_id=employee_id)
            except Exception as e:
                # If user creation fails, rollback employee (optional)
                self.db.execute("UPDATE employees SET active = 0 WHERE id = ?", (employee_id,))
                raise Exception(f"Employee created but user account failed: {e}")
        
        return employee_id

    def edit_employee(self, employee_id: int, updates: dict) -> bool:
        self._check_admin()
        allowed = {"full_name", "role", "department", "contact", "rate", "active"}
        set_parts = []
        params = []
        for k, v in updates.items():
            if k in allowed:
                set_parts.append(f"{k} = ?")
                params.append(v)
        if not set_parts:
            return False
        params.append(employee_id)
        self.db.execute(f"UPDATE employees SET {', '.join(set_parts)} WHERE id = ?", tuple(params))
        return True

    def delete_employee(self, employee_id: int) -> bool:
        """Soft-delete employee (mark inactive) and disable linked user."""
        self._check_admin()
        # mark employee as inactive
        self.db.execute("UPDATE employees SET active = 0 WHERE id = ?", (employee_id,))
        # disable linked user account
        self.db.execute("UPDATE users SET active = 0 WHERE employee_id = ?", (employee_id,))
        return True

    def get_employee(self, employee_id: int):
        self._check_admin()
        return self.db.fetchone("SELECT id, full_name, role, department, contact, rate, active FROM employees WHERE id = ?", (employee_id,))

    def list_employees(self):
        self._check_admin()
        return self.db.query("SELECT id, full_name, role, department, contact, rate, active FROM employees WHERE active = 1 ORDER BY id")

    # --- CLI handlers ---
    def handle_employees(self):
        view = self.view
        if view is None:
            print("No view configured")
            return

        while True:
            view.display_employees_menu()
            ch = view.prompt_for_input("Choose (number): ").strip()
            if ch == "1":  # Add
                try:
                    full_name = view.prompt_for_input("Full name: ").strip()
                    if not full_name:
                        view.display_error("Full name required")
                        continue
                    role = view.prompt_for_input("Role: ").strip()
                    if not role:
                        view.display_error("Role required")
                        continue
                    department = view.prompt_for_input("Department: ").strip()
                    contact = view.prompt_for_input("Contact: ").strip()
                    rate_s = view.prompt_for_input("Hourly rate: ").strip()
                    if not rate_s:
                        view.display_error("Hourly rate required")
                        continue
                    rate = float(rate_s)
                    
                    # Ask if admin wants to create login credentials
                    create_creds = view.prompt_for_input("Create login credentials? (y/n): ").strip().lower()
                    username = None
                    password = None
                    
                    if create_creds == "y":
                        username = view.prompt_for_input("Username: ").strip()
                        if not username:
                            view.display_error("Username required")
                            continue
                        password = view.prompt_for_input("Password: ").strip()
                        if not password:
                            view.display_error("Password required")
                            continue
                    
                    eid = self.add_employee(full_name, role, department, contact, rate, username, password)
                    if username:
                        view.display_success(f"Employee added with ID {eid}\nLogin credentials created: {username}")
                    else:
                        view.display_success(f"Employee added with ID {eid}")
                except ValueError:
                    view.display_error("Invalid rate (must be a number)")
                except PermissionError as e:
                    view.display_error(str(e))
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "2":  # List
                try:
                    rows = self.list_employees()
                    view.display_employees_list(rows)
                except PermissionError as e:
                    view.display_error(str(e))
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "3":  # View
                try:
                    eid_s = view.prompt_for_input("Employee ID: ").strip()
                    if not eid_s:
                        view.display_error("Employee ID required")
                        continue
                    eid = int(eid_s)
                except ValueError:
                    view.display_error("Invalid id")
                    continue
                try:
                    row = self.get_employee(eid)
                    if not row:
                        view.display_error("Employee not found")
                    else:
                        view.display_employee(row)
                except PermissionError as e:
                    view.display_error(str(e))
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "4":  # Edit
                try:
                    eid_s = view.prompt_for_input("Employee ID to edit: ").strip()
                    if not eid_s:
                        view.display_error("Employee ID required")
                        continue
                    eid = int(eid_s)
                except ValueError:
                    view.display_error("Invalid id")
                    continue
                try:
                    updates = {}
                    full_name = view.prompt_for_input("New full name (blank to skip): ").strip()
                    if full_name:
                        updates["full_name"] = full_name
                    role = view.prompt_for_input("New role (blank to skip): ").strip()
                    if role:
                        updates["role"] = role
                    department = view.prompt_for_input("New department (blank to skip): ").strip()
                    if department:
                        updates["department"] = department
                    contact = view.prompt_for_input("New contact (blank to skip): ").strip()
                    if contact:
                        updates["contact"] = contact
                    rate_s = view.prompt_for_input("New hourly rate (blank to skip): ").strip()
                    if rate_s:
                        updates["rate"] = float(rate_s)
                    if self.edit_employee(eid, updates):
                        view.display_success("Employee updated")
                    else:
                        view.display_error("No fields updated")
                except ValueError:
                    view.display_error("Invalid input")
                except PermissionError as e:
                    view.display_error(str(e))
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "5":  # Delete
                try:
                    eid_s = view.prompt_for_input("Employee ID to delete: ").strip()
                    if not eid_s:
                        view.display_error("Employee ID required")
                        continue
                    eid = int(eid_s)
                except ValueError:
                    view.display_error("Invalid id")
                    continue
                try:
                    confirm = view.prompt_for_input("Confirm delete (y/n): ").strip().lower()
                    if confirm == "y":
                        self.delete_employee(eid)
                        view.display_success("Employee deleted (deactivated)")
                    else:
                        view.display_message("Cancelled")
                except PermissionError as e:
                    view.display_error(str(e))
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "6":  # Back
                break
            else:
                view.display_invalid_choice_message()
