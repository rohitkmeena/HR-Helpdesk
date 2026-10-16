from django.db import models

class Employee(models.Model):
    employee_id = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=120, db_index=True)
    email = models.EmailField(unique=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    joining_date = models.DateField()
    manager = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='Active')

    class Meta:
        ordering = ['employee_id']

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class LeaveBalance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField(default=2026)
    annual_leave = models.DecimalField(max_digits=5, decimal_places=1, default=20.0)
    sick_leave = models.DecimalField(max_digits=5, decimal_places=1, default=10.0)
    casual_leave = models.DecimalField(max_digits=5, decimal_places=1, default=5.0)
    parental_leave = models.DecimalField(max_digits=5, decimal_places=1, default=60.0)
    comp_off = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['employee', 'year'], name='unique_employee_leave_year')
        ]
        ordering = ['employee', '-year']

    def __str__(self):
        return f"{self.employee.employee_id} ({self.year}) Leave Balance"


class Payslip(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payslips')
    month = models.CharField(max_length=20)
    year = models.IntegerField(default=2026)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    hra = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2)
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    pf_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    insurance_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    payment_status = models.CharField(max_length=20, default='Paid')
    disbursement_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['employee', 'month', 'year'], name='unique_employee_payslip_period')
        ]
        ordering = ['-year', '-disbursement_date']

    def __str__(self):
        return f"{self.employee.employee_id} Payslip - {self.month} {self.year}"


class HRPolicy(models.Model):
    policy_id = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    content = models.TextField()

    class Meta:
        ordering = ['policy_id']

    def __str__(self):
        return f"{self.policy_id} - {self.title}"


class LeaveRequest(models.Model):
    request_id = models.CharField(max_length=50, unique=True, db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=50)
    start_date = models.DateField()
    end_date = models.DateField()
    working_days_requested = models.IntegerField()
    calendar_days = models.IntegerField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=30, default='Pending Approval')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.request_id} - {self.employee.employee_id} ({self.status})"