
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import csv
import threading

app = FastAPI(title="Aroha Attendance System")

# Project folder
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
CSV_FILE = BASE_DIR / "attendance.csv"

# Prevent simultaneous writes from interfering
csv_lock = threading.Lock()

COMPANY_LOCATION = (
    "#14, 5th Main, 38th Cross, 5th Block, "
    "Jayanagar, Bangalore - 560041"
)

COLUMNS = [
    "Employee ID",
    "Employee Name",
    "Date",
    "Location",
    "Login Time",
    "Logout Time"
]


# Create CSV with headers if it does not exist
if not CSV_FILE.exists():
    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(COLUMNS)


# Login request data
class LoginRequest(BaseModel):
    empId: str
    empName: str
    date: str
    login: str


# Logout request data
class LogoutRequest(BaseModel):
    empId: str
    date: str


# ---------------- LOGIN API ----------------

@app.post("/api/login")
def submit_login(data: LoginRequest):

    emp_id = data.empId.strip()
    emp_name = data.empName.strip()

    if not emp_id or not emp_name:
        raise HTTPException(400, "Employee ID and name are required.")

    try:
        datetime.strptime(data.date, "%Y-%m-%d")
        datetime.strptime(data.login, "%H:%M")
    except ValueError:
        raise HTTPException(400, "Invalid date or login time.")

    with csv_lock:

        with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as file:
            records = list(csv.DictReader(file))

        # Prevent duplicate login for the same employee and date
        for record in records:
            if (
                record["Employee ID"].strip().lower() == emp_id.lower()
                and record["Date"] == data.date
            ):
                raise HTTPException(
                    409,
                    "Attendance has already been submitted for this date."
                )

        new_record = {
            "Employee ID": emp_id,
            "Employee Name": emp_name,
            "Date": data.date,
            "Location": COMPANY_LOCATION,
            "Login Time": data.login,
            "Logout Time": ""
        }

        with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writerow(new_record)

    return {"message": "Login attendance saved successfully."}


# ---------------- LOGOUT API ----------------

@app.post("/api/logout")
def submit_logout(data: LogoutRequest):

    emp_id = data.empId.strip()

    if not emp_id:
        raise HTTPException(400, "Employee ID is required.")

    with csv_lock:

        with open(CSV_FILE, "r", newline="", encoding="utf-8-sig") as file:
            records = list(csv.DictReader(file))

        found = False

        for record in records:
            if (
                record["Employee ID"].strip().lower() == emp_id.lower()
                and record["Date"] == data.date
            ):
                if record["Logout Time"]:
                    raise HTTPException(
                        409,
                        "Logout time has already been recorded."
                    )

                # Record the time from the computer running FastAPI
                record["Logout Time"] = datetime.now().strftime("%H:%M")
                found = True
                break

        if not found:
            raise HTTPException(
                404,
                "Login attendance was not found."
            )

        # Rewrite CSV with the updated logout time
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(records)

    return {"message": "Logout attendance saved successfully."}


# Serve HTML and logo
app.mount(
    "/",
    StaticFiles(directory=STATIC_DIR, html=True),
    name="static"
)
