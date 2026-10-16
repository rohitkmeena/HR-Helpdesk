# HR-Helpdesk

An autonomous AI-powered HR Helpdesk built with **Django**, **Google Gemini API** (`google-genai`), and **Supabase PostgreSQL** for the hackathon.

It answers three core HR topics:
1. **Employee leave balance**
2. **Employee payslip**
3. **Company policy**

It also provides the required compute, write, and live tools:
- **Compute Tool**: Leave-days calculator (`calculate_leave_days` in Python)
- **Write Tool**: Submit and persist leave requests to PostgreSQL (`submit_leave_request`)
- **Live Tool**: Real-time current date and time (`get_current_datetime`)

---

## Key Features & Constraints

- **Real Gemini Function Calling**: Dynamic tool selection with official `google-genai` Python SDK.
- **Strict Data Integrity**: Factual answers retrieved directly from Supabase PostgreSQL models. If a record is missing, the model honestly answers that it was not found in the database—**never invents answers**.
- **5-Round Safeguard**: Tool execution loop is capped at five rounds to guarantee low latency.
- **Django ORM & PostgreSQL**: All data operations run through Django models (`Employee`, `LeaveBalance`, `Payslip`, `HRPolicy`, `LeaveRequest`).
- **Single Page Q&A Interface**: Single clean page with an answer card and execution trace for transparency.
- **Pre-seeded Database Data**: 20 fake employees, full leave balances, multi-month itemized payslips, and 8 comprehensive HR policies. Seed command is **100% idempotent** (safe to run multiple times using `update_or_create`).

---

## Setup Instructions

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Set your Gemini API key and Supabase PostgreSQL connection string (`DATABASE_URL`):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Supabase PostgreSQL Connection String
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

SECRET_KEY=django-insecure-hr-helpdesk-hackathon-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Run Database Migrations
```powershell
python manage.py migrate
```

### 4. Seed Database
```powershell
python manage.py seed_data
```
*(Idempotently seeds 20 employees, 20 leave balances, 40 payslips, and 8 HR policies)*

### 5. Run the Test Suite (Optional)
```powershell
python manage.py test
```

### 6. Start the Server
```powershell
python manage.py runserver
```

Open your browser at:
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## Three Core HR Topics & Sample Questions

| HR Topic | Tool | Example Question |
| :--- | :--- | :--- |
| **1. Leave Balance** | `get_leave_balance` | *"What is the annual leave balance for employee EMP001?"* |
| **2. Payslip** | `get_payslip` | *"Show me the latest payslip for Alice Johnson (EMP001)."* |
| **3. Company Policy** | `get_hr_policy` | *"What is our company policy on remote work and internet reimbursement?"* |
| **Compute Tool** | `calculate_leave_days` | *"How many working business days between 2026-10-12 and 2026-10-16?"* |
| **Write Tool** | `submit_leave_request` | *"Submit an annual leave request for EMP001 from 2026-11-09 to 2026-11-13 for vacation."* |
| **Live Tool** | `get_current_datetime` | *"What is today's date and time?"* |
