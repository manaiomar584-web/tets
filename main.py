import os
import json
import base64
import io
import secrets
import hashlib
from datetime import datetime
from typing import Optional, List, Any

from fastapi import FastAPI, Request, HTTPException, Depends, status, Form, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import pandas as pd

import database as db
import pdf_gen

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize databases and create default users on startup
    db.init_dbs()
    yield

app = FastAPI(title="Aster Informatique - Repair Tracker", lifespan=lifespan)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="."), name="static")

# Simple session store
SESSIONS = {}
SESSION_COOKIE = "repair_session"

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class JobPayload(BaseModel):
    customerName: str
    phoneNumber: Optional[str] = ""
    deviceType: str
    status: str
    brandModel: Optional[str] = ""
    serialNumber: Optional[str] = ""
    productNumber: Optional[str] = ""
    scanReference: Optional[str] = ""
    receivedDate: str
    deliveryDecision: Optional[str] = "Pending"
    deliveredDate: Optional[str] = ""
    amount: Optional[str] = ""
    paidStatus: Optional[str] = "No"
    problem: Optional[str] = ""
    repairDone: Optional[str] = ""
    notes: Optional[str] = ""
    accessories: Optional[List[str]] = []
    otherAccessory: Optional[str] = ""
    deviceCondition: Optional[List[str]] = []
    conditionRemarks: Optional[str] = ""
    technicianName: Optional[str] = ""
    returnCondition: Optional[List[str]] = []
    isSubcontracted: Optional[str] = "No"
    subcontractCompany: Optional[str] = ""
    subcontractSentDate: Optional[str] = ""
    subcontractReturnStatus: Optional[str] = "Pending"
    subcontractReturnedDate: Optional[str] = ""
    subcontractNotes: Optional[str] = ""

class ScanPayload(BaseModel):
    scanCode: str
    customerName: Optional[str] = "Client comptoir"
    deviceType: Optional[str] = "Computer"
    brandModel: Optional[str] = ""

class ImportPayload(BaseModel):
    content_base64: str

# Helper functions
def get_current_user(repair_session: Optional[str] = Cookie(None)):
    if not repair_session or repair_session not in SESSIONS:
        return None
    return SESSIONS[repair_session]

def require_auth(user: Any = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Non autorise")
    return user

def require_admin(user: Any = Depends(require_auth)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acces reserve a l'administrateur")
    return user

def generate_product_number(device_type: str):
    type_codes = {
        "Computer": "PC", "Laptop": "LP", "Desktop": "DT", "PDA": "PD",
        "Phone": "PH", "Tablet": "TB", "Smart Watch": "SW", "Camera": "CM",
        "CCTV": "CV", "Monitor": "MN", "Television": "TV", "Printer": "PR",
        "Scanner": "SC", "Projector": "PJ", "Game Console": "GC", "Speaker": "SP",
        "Amplifier": "AM", "Router": "RT", "Modem": "MD", "POS Terminal": "PS",
        "UPS": "UP", "Inverter": "IV", "Power Supply": "PW", "Keyboard": "KB",
        "Mouse": "MS", "External Drive": "ED", "Other": "OT"
    }
    prefix = type_codes.get(device_type, "XX")
    with db.get_db(db.PRODUCT_DB) as conn:
        conn.execute("INSERT OR IGNORE INTO counters (prefix, next_value) VALUES (?, 1)", (prefix,))
        row = conn.execute("SELECT next_value FROM counters WHERE prefix = ?", (prefix,)).fetchone()
        val = row["next_value"]
        conn.execute("UPDATE counters SET next_value = next_value + 1 WHERE prefix = ?", (prefix,))
        conn.commit()
    return f"{prefix}{str(val).zfill(5)}"

def row_to_dict(row):
    if not row:
        return None
    d = dict(row)
    for key in ["accessories", "device_condition", "return_condition"]:
        if key in d and d[key]:
            try:
                d[key] = json.loads(d[key])
            except:
                d[key] = []
        else:
            d[key] = []
    return d

# Routes
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/session")
async def get_session(user: Any = Depends(get_current_user)):
    return {"user": user}

@app.post("/api/login")
async def api_login(req: LoginRequest, response: Response):
    with db.get_db(db.USER_DB) as conn:
        user_row = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
        if user_row and db.verify_password(req.password, user_row["password_hash"]):
            user_data = {
                "id": user_row["id"],
                "username": user_row["username"],
                "role": user_row["role"],
                "full_name": user_row["full_name"]
            }
            token = secrets.token_urlsafe(24)
            SESSIONS[token] = user_data
            response.set_cookie(key=SESSION_COOKIE, value=token, httponly=True, samesite="lax")
            return {"user": user_data}
    raise HTTPException(status_code=401, detail="Identifiants invalides")

@app.post("/api/logout")
async def api_logout(response: Response, repair_session: Optional[str] = Cookie(None)):
    if repair_session in SESSIONS:
        del SESSIONS[repair_session]
    response.delete_cookie(key=SESSION_COOKIE)
    return {"ok": True}

@app.get("/api/jobs")
async def get_jobs(user: Any = Depends(require_auth)):
    with db.get_db(db.PRODUCT_DB) as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return {"jobs": [row_to_dict(r) for r in rows]}

@app.post("/api/jobs")
async def create_job(payload: JobPayload, user: Any = Depends(require_auth)):
    job_id = f"JOB-{secrets.randbelow(900000) + 100000}"
    id = secrets.token_hex(16)
    product_number = generate_product_number(payload.deviceType)
    now = datetime.now().isoformat()
    
    with db.get_db(db.PRODUCT_DB) as conn:
        conn.execute("""
            INSERT INTO jobs (id, job_id, product_number, scan_reference, customer_name, phone_number,
                device_type, status, brand_model, serial_number, received_date, delivery_decision,
                delivered_date, amount, paid_status, problem, repair_done, notes, accessories,
                other_accessory, device_condition, condition_remarks, technician_name, return_condition,
                is_subcontracted, subcontract_company, subcontract_sent_date, subcontract_return_status,
                subcontract_returned_date, subcontract_notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id, job_id, product_number, payload.scanReference, payload.customerName, payload.phoneNumber,
              payload.deviceType, payload.status, payload.brandModel, payload.serialNumber, payload.receivedDate,
              payload.deliveryDecision, payload.deliveredDate, payload.amount, payload.paidStatus, payload.problem,
              payload.repairDone, payload.notes, json.dumps(payload.accessories), payload.otherAccessory,
              json.dumps(payload.deviceCondition), payload.conditionRemarks, payload.technicianName,
              json.dumps(payload.returnCondition), payload.isSubcontracted, payload.subcontractCompany,
              payload.subcontractSentDate, payload.subcontractReturnStatus, payload.subcontractReturnedDate,
              payload.subcontractNotes, now, now))
        conn.commit()
    return {"status": "ok"}

@app.post("/api/jobs/scan")
async def scan_job(payload: ScanPayload, user: Any = Depends(require_auth)):
    job_id = f"JOB-{secrets.randbelow(900000) + 100000}"
    id = secrets.token_hex(16)
    product_number = generate_product_number(payload.deviceType)
    now = datetime.now().isoformat()
    today = datetime.now().date().isoformat()
    
    with db.get_db(db.PRODUCT_DB) as conn:
        conn.execute("""
            INSERT INTO jobs (id, job_id, product_number, scan_reference, customer_name,
                device_type, status, brand_model, received_date, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (id, job_id, product_number, payload.scanCode, payload.customerName,
              payload.deviceType, "Received", payload.brandModel, today, 
              "Cree depuis l'enregistrement rapide.", now, now))
        conn.commit()
    return {"status": "ok"}

@app.put("/api/jobs/{id}")
async def update_job(id: str, payload: JobPayload, user: Any = Depends(require_auth)):
    now = datetime.now().isoformat()
    with db.get_db(db.PRODUCT_DB) as conn:
        cursor = conn.execute("""
            UPDATE jobs SET customer_name=?, phone_number=?, device_type=?, status=?, 
            brand_model=?, serial_number=?, scan_reference=?, received_date=?, delivery_decision=?, 
            delivered_date=?, amount=?, paid_status=?, problem=?, repair_done=?, notes=?, 
            accessories=?, other_accessory=?, device_condition=?, condition_remarks=?, technician_name=?, 
            return_condition=?, is_subcontracted=?, subcontract_company=?, subcontract_sent_date=?, 
            subcontract_return_status=?, subcontract_returned_date=?, subcontract_notes=?, 
            updated_at=? WHERE id=?
        """, (payload.customerName, payload.phoneNumber, payload.deviceType, payload.status,
              payload.brandModel, payload.serialNumber, payload.scanReference, payload.receivedDate,
              payload.deliveryDecision, payload.deliveredDate, payload.amount, payload.paidStatus,
              payload.problem, payload.repairDone, payload.notes, json.dumps(payload.accessories),
              payload.otherAccessory, json.dumps(payload.deviceCondition), payload.conditionRemarks,
              payload.technicianName, json.dumps(payload.returnCondition), payload.isSubcontracted,
              payload.subcontractCompany, payload.subcontractSentDate, payload.subcontractReturnStatus,
              payload.subcontractReturnedDate, payload.subcontractNotes, now, id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dossier non trouve")
        conn.commit()
    return {"status": "ok"}

@app.delete("/api/jobs/{id}")
async def delete_job(id: str, user: Any = Depends(require_admin)):
    with db.get_db(db.PRODUCT_DB) as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id=?", (id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dossier non trouve")
        conn.commit()
    return {"ok": True}

@app.delete("/api/jobs")
async def clear_all_jobs(user: Any = Depends(require_admin)):
    with db.get_db(db.PRODUCT_DB) as conn:
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM counters")
        conn.commit()
    return {"ok": True}

@app.get("/api/jobs/{id}/pdf")
async def get_job_pdf(id: str, type: str = "depot", user: Any = Depends(require_auth)):
    with db.get_db(db.PRODUCT_DB) as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dossier non trouve")
        job = dict(row)
        pdf_bytes = pdf_gen.generate_job_pdf(job, type=type)
        return Response(content=bytes(pdf_bytes), media_type="application/pdf", 
                        headers={"Content-Disposition": f"attachment; filename={type}_{job['product_number']}.pdf"})

@app.get("/api/customers/search")
async def search_customers(q: str = "", user: Any = Depends(require_auth)):
    with db.get_db(db.PRODUCT_DB) as conn:
        rows = conn.execute(
            "SELECT DISTINCT customer_name, phone_number FROM jobs "
            "WHERE customer_name LIKE ? OR phone_number LIKE ? LIMIT 10",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
        return {"customers": [{"name": r["customer_name"], "phone": r["phone_number"]} for r in rows]}

@app.get("/api/export")
async def export_jobs(user: Any = Depends(require_auth)):
    with db.get_db(db.PRODUCT_DB) as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    
    jobs = [row_to_dict(r) for r in rows]
    export_rows = []
    for job in jobs:
        export_rows.append({
            "Code unique": job.get("product_number"),
            "Numero interne": job.get("job_id"),
            "Client": job.get("customer_name"),
            "Telephone": job.get("phone_number"),
            "Type appareil": job.get("device_type"),
            "Statut": job.get("status"),
            "Marque modele": job.get("brand_model"),
            "Numero de serie": job.get("serial_number"),
            "SN PN": job.get("scan_reference"),
            "Date depot": job.get("received_date"),
            "Decision sortie": job.get("delivery_decision"),
            "Date sortie": job.get("delivered_date"),
            "Montant": job.get("amount"),
            "Paiement recu": job.get("paid_status"),
            "Panne signalee": job.get("problem"),
            "Travail effectue": job.get("repair_done"),
            "Notes": job.get("notes"),
            "Accessoires": ", ".join(job.get("accessories", [])),
            "Autre accessoire": job.get("other_accessory"),
            "Etat appareil": ", ".join(job.get("device_condition", [])),
            "Remarques etat": job.get("condition_remarks"),
            "Technicien": job.get("technician_name"),
            "Etat restitution": ", ".join(job.get("return_condition", [])),
            "Sous-traitance": job.get("is_subcontracted"),
            "Societe externe": job.get("subcontract_company"),
            "Date envoi": job.get("subcontract_sent_date"),
            "Etat retour": job.get("subcontract_return_status"),
            "Date retour": job.get("subcontract_returned_date"),
            "Notes sous-traitance": job.get("subcontract_notes")
        })
    
    output = io.BytesIO()
    pd.DataFrame(export_rows).to_excel(output, index=False)
    output.seek(0)
    
    filename = f"suivi_reparation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/import")
async def import_jobs(payload: ImportPayload, user: Any = Depends(require_admin)):
    try:
        content = base64.b64decode(payload.content_base64)
        df = pd.read_excel(io.BytesIO(content)).fillna("")
        imported = 0
        now = datetime.now().isoformat()
        
        with db.get_db(db.PRODUCT_DB) as conn:
            for _, row in df.iterrows():
                id = secrets.token_hex(16)
                job_id = row.get("Numero interne") or f"JOB-{secrets.randbelow(900000) + 100000}"
                prod_num = row.get("Code unique") or generate_product_number(row.get("Type appareil", "Other"))
                
                conn.execute("""
                    INSERT INTO jobs (id, job_id, product_number, customer_name, phone_number,
                        device_type, status, brand_model, serial_number, scan_reference, 
                        received_date, delivery_decision, delivered_date, amount, paid_status, 
                        problem, repair_done, notes, accessories, other_accessory, device_condition,
                        condition_remarks, technician_name, return_condition, is_subcontracted,
                        subcontract_company, subcontract_sent_date, subcontract_return_status, 
                        subcontract_returned_date, subcontract_notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (id, job_id, prod_num, row.get("Client"), row.get("Telephone"),
                      row.get("Type appareil"), row.get("Statut"), row.get("Marque modele"),
                      row.get("Numero de serie"), row.get("SN PN"), row.get("Date depot"),
                      row.get("Decision sortie"), row.get("Date sortie"), row.get("Montant"),
                      row.get("Paiement recu"), row.get("Panne signalee"), row.get("Travail effectue"),
                      row.get("Notes"), "[]", row.get("Autre accessoire"), "[]",
                      row.get("Remarques etat"), row.get("Technicien"), "[]", row.get("Sous-traitance"),
                      row.get("Societe externe"), row.get("Date envoi"), row.get("Etat retour"),
                      row.get("Date retour"), row.get("Notes sous-traitance"), now, now))
                imported += 1
            conn.commit()
        return {"imported": imported}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur d'importation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    db.init_dbs()
    uvicorn.run(app, host="0.0.0.0", port=8000)

