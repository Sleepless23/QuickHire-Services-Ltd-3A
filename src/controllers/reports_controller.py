from typing import Optional
from calendar import monthrange
from models.database import Database

class ReportsController:
    def __init__(self, db, view, payroll_service=None, attendance_controller=None, current_user=None):
        self.db = db
        self.view = view
        self.payroll_service = payroll_service
        self.attendance_controller = attendance_controller
        self.current_user = current_user

    def _check_admin(self):
        """Raise error if not admin."""
        if not getattr(self.current_user, "is_hr", False):
            raise PermissionError("Only admins can access reports")

    def generate_monthly_report(self, year: int, month: int):
        payroll = self.payroll_service.generate_payroll_for_month(year, month)
        days = monthrange(year, month)[1]
        attendance_summary = {}
        for rec in payroll:
            emp_id = rec["employee_id"]
            total = 0.0
            for d in range(1, days + 1):
                date = f"{year:04d}-{month:02d}-{d:02d}"
                stats = self.attendance_controller.compute_hours_for_day(emp_id, date)
                total += stats.get("total_hours", 0.0)
            attendance_summary[emp_id] = total

        report = {"payroll": payroll, "attendance_summary": attendance_summary}
        if self.view and hasattr(self.view, "display_report"):
            self.view.display_report(report)
        else:
            print(report)
        return report

    def export_monthly_report_csv(self, year: int, month: int, out_path: Optional[str] = None):
        # delegate to payroll_service export (it persists payroll_runs)
        return self.payroll_service.export_monthly_csv(year, month, out_path)

    def handle_reports(self):
        view = self.view
        if view is None:
            print("No view configured")
            return
        
        try:
            self._check_admin()
        except PermissionError as e:
            view.display_error(str(e))
            return

        while True:
            view.display_reports_menu()
            ch = view.prompt_for_input("Choose (number): ").strip()
            if ch == "1":  # Attendance report
                try:
                    eid_s = view.prompt_for_input("Employee ID: ").strip()
                    if not eid_s:
                        view.display_error("Employee ID required")
                        continue
                    eid = int(eid_s)
                    start = view.prompt_for_input("Start date (YYYY-MM-DD) or blank: ").strip() or None
                    end = view.prompt_for_input("End date (YYYY-MM-DD) or blank: ").strip() or None
                    recs = self.attendance_controller.list_records(eid, start, end)
                    view.display_attendance_records(recs)
                except ValueError:
                    view.display_error("Invalid employee ID")
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "2":  # Payroll report
                try:
                    year_s = view.prompt_for_input("Year (YYYY): ").strip()
                    month_s = view.prompt_for_input("Month (1-12): ").strip()
                    if not year_s or not month_s:
                        view.display_error("Year and Month required")
                        continue
                    year = int(year_s)
                    month = int(month_s)
                    if not (1 <= month <= 12):
                        view.display_error("Month must be 1-12")
                        continue
                    results = self.payroll_service.generate_payroll_for_month(year, month)
                    if results:
                        view.display_message(f"\nPayroll Report {year}-{month:02d}:\n")
                        for r in results:
                            full_name = r.get("full_name", "Unknown")
                            net = r.get("net", 0)
                            gross = r.get("gross", 0)
                            view.display_message(f"  {full_name}: Gross=${gross} | Net=${net}")
                    else:
                        view.display_message("No payroll data found")
                except ValueError:
                    view.display_error("Invalid year/month")
                except Exception as e:
                    view.display_error(f"Error: {e}")
            elif ch == "3":  # Back
                break
            else:
                view.display_invalid_choice_message()
