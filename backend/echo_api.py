"""Echo's local application API. Visitor submission stays available while PIN locked."""
import secrets
import os
import time
from datetime import date, datetime, timezone
from datetime import date as Date
from functools import lru_cache
from threading import Lock
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, model_validator
from knowledge import RULES, SUGGESTIONS
from security import hash_secret, verify
import store
from echo_analytics import baseline, dashboard, monthly, patterns, progress
from review_pipeline import process_review

router = APIRouter(prefix="/api")
model_lock = Lock()

def now():
    return datetime.now(timezone.utc).isoformat()

@lru_cache(maxsize=1)
def classifier():
    from insight_model import InsightModel
    return InsightModel()

def initialize(seed_demo=None):
    store.initialize()
    with store.connect() as db:
        if not db.execute("SELECT 1 FROM users WHERE username='noor'").fetchone():
            db.execute("INSERT OR IGNORE INTO users(id,username,password_hash,display_name,pin_hash) VALUES(?,?,?,?,?)",
                       (str(uuid4()), "noor", hash_secret("coffee2025"), "Noor", hash_secret("0000")))
        user_id = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
    if seed_demo is None:
        seed_demo = os.environ.get("ECHO_SEED_DEMO", "1") != "0"
    if seed_demo:
        from demo_data import seed_bundled_demo
        seed_bundled_demo(user_id)

def session(request: Request):
    with store.connect() as db:
        row = db.execute("SELECT s.*,u.username,u.display_name,u.last_seen FROM sessions s JOIN users u ON u.id=s.user_id WHERE token=? AND expires>?", (request.cookies.get("echo_session", ""), time.time())).fetchone()
    if not row:
        raise HTTPException(401, "Log in to this local device first.")
    return dict(row)

def owner(s=Depends(session)):
    if not s["unlocked"]:
        raise HTTPException(403, "Unlock the dashboard with your PIN.")
    return s

def get_record(table, id, user_id, deleted=False):
    record = next((r for r in store.records(table, user_id, deleted) if r["id"] == id), None)
    if record is None:
        raise HTTPException(404, "Record not found.")
    return record

class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="Owner", min_length=1, max_length=80)

def new_session(user_id, response):
    token = secrets.token_urlsafe(32)
    with store.connect() as db:
        db.execute("INSERT INTO sessions VALUES(?,?,?,0)", (token, user_id, time.time()+86400))
    response.set_cookie("echo_session", token, httponly=True, samesite="strict", max_age=86400)

@router.post("/auth/signup", status_code=201)
def signup(payload: Credentials, response: Response):
    import sqlite3
    id = str(uuid4())
    try:
        with store.connect() as db:
            db.execute("INSERT INTO users(id,username,password_hash,display_name,pin_hash) VALUES(?,?,?,?,?)", (id, payload.username.lower(), hash_secret(payload.password), payload.display_name, hash_secret("0000")))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username already exists.")
    new_session(id, response)
    return {"username": payload.username.lower(), "display_name": payload.display_name}

@router.post("/auth/login")
def login(payload: Credentials, response: Response):
    with store.connect() as db:
        user = db.execute("SELECT * FROM users WHERE username=?", (payload.username.lower(),)).fetchone()
    if not user or not verify(payload.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect username or password.")
    new_session(user["id"], response)
    return {"username": user["username"], "display_name": user["display_name"]}

@router.get("/auth/me")
def me(s=Depends(session)):
    return {"username": s["username"], "display_name": s["display_name"], "unlocked": bool(s["unlocked"])}

@router.post("/auth/logout")
def logout(response: Response, s=Depends(session)):
    with store.connect() as db:
        db.execute("DELETE FROM sessions WHERE token=?", (s["token"],))
    response.delete_cookie("echo_session")
    return {"ok": True}

class PinPayload(BaseModel):
    pin: str = Field(pattern=r"^\d{4}$")

@router.post("/pin/unlock")
def unlock(payload: PinPayload, s=Depends(session)):
    with store.connect() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (s["user_id"],)).fetchone()
        if user["lock_until"] > time.time():
            raise HTTPException(429, {"message": "Temporary PIN lockout.", "retry_after": max(1, int(user["lock_until"]-time.time()))})
        if not verify(payload.pin, user["pin_hash"]):
            attempts = user["failed_attempts"] + 1
            locked = time.time()+30 if attempts >= 5 else 0
            db.execute("UPDATE users SET failed_attempts=?,lock_until=? WHERE id=?", (0 if locked else attempts, locked, s["user_id"]))
        else:
            db.execute("UPDATE users SET failed_attempts=0,lock_until=0 WHERE id=?", (s["user_id"],))
            db.execute("UPDATE sessions SET unlocked=1 WHERE token=?", (s["token"],))
            return {"unlocked": True}
    raise HTTPException(429 if locked else 401, {"message": "Incorrect PIN.", "retry_after": 30 if locked else 0})

@router.post("/pin/lock")
def lock(s=Depends(session)):
    with store.connect() as db:
        db.execute("UPDATE sessions SET unlocked=0 WHERE token=?", (s["token"],))
    return {"unlocked": False}

@router.patch("/pin")
def change_pin(payload: PinPayload, s=Depends(owner)):
    with store.connect() as db:
        db.execute("UPDATE users SET pin_hash=? WHERE id=?", (hash_secret(payload.pin), s["user_id"]))
    return {"ok": True}

class ReviewPayload(BaseModel):
    rating: int = Field(ge=1, le=5, strict=True)
    date: Date = Field(default_factory=Date.today)
    favorite_en: str = Field(default="", max_length=2000)
    improvement_en: str = Field(default="", max_length=2000)
    share_consent: bool = False
    language: str = "en"

    @model_validator(mode="after")
    def validate_text(self):
        if self.language != "en":
            raise ValueError("Visitor input must be English for English-to-Kiswahili translation.")
        if not any(c.isalnum() for c in self.favorite_en + self.improvement_en):
            raise ValueError("At least one meaningful text field is required.")
        if self.date > date.today():
            raise ValueError("Review date cannot be in the future.")
        return self

@router.post("/reviews", status_code=201)
def submit(payload: ReviewPayload, s=Depends(session)):
    try:
        with model_lock:
            from translate_opus import translate
            record = process_review(payload.model_dump(mode="json"), translate, classifier())
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(503, "Local processing failed; review was not saved. Check installed models or shorten the text.") from error
    return store.put("reviews", record, s["user_id"])

@router.get("/reviews")
def reviews(filter: str = "all", include_deleted: bool = False, s=Depends(owner)):
    if filter not in {"all", "5", "4", "3", "complaint", "not_sure"}:
        raise HTTPException(422, "Unknown review filter.")
    result = store.records("reviews", s["user_id"], include_deleted)
    result = [r for r in result if filter == "all" or filter in {"4", "5"} and r["rating"] == int(filter) or filter == "3" and r["rating"] <= 3 or filter == "complaint" and any(p["sentiment"] == "negative" for p in r["topics"]) or filter == "not_sure" and r["classification_status"] == "not_sure"]
    return sorted(result, key=lambda r: r["created_at"], reverse=True)

@router.post("/reviews/seen")
def seen(s=Depends(owner)):
    with store.connect() as db:
        db.execute("UPDATE users SET last_seen=? WHERE id=?", (now(), s["user_id"]))
        db.execute("UPDATE reviews SET data=json_set(data,'$.owner_seen',json('true')) WHERE user_id=? AND deleted=0", (s["user_id"],))
    return {"ok": True}

@router.get("/reviews/{id}")
def review(id: str, s=Depends(owner)):
    return get_record("reviews", id, s["user_id"])

@router.delete("/reviews/{id}")
def delete_review(id: str, s=Depends(owner)):
    r = get_record("reviews", id, s["user_id"])
    r["deleted"] = True
    return store.put("reviews", r, s["user_id"])

@router.patch("/reviews/{id}/restore")
def restore(id: str, s=Depends(owner)):
    r = get_record("reviews", id, s["user_id"], True)
    r["deleted"] = False
    return store.put("reviews", r, s["user_id"])

class ManualTopic(BaseModel):
    topic: str
    sentiment: str

class Correction(BaseModel):
    topics: list[ManualTopic] = Field(default_factory=list, max_length=14)
    checked: bool = True

@router.patch("/reviews/{id}/classification")
def correction(id: str, payload: Correction, s=Depends(owner)):
    if any(p.topic not in RULES["topics"] or p.sentiment not in {"positive", "negative", "neutral", "request"} for p in payload.topics):
        raise HTTPException(422, "Unknown topic or sentiment.")
    r = get_record("reviews", id, s["user_id"])
    r["manual_override"] = payload.model_dump()
    r["checked"] = payload.checked
    r["topics"] = [{**p.model_dump(), "classifier_score": None, "method": "manual", "field": "favorite" if p.sentiment == "positive" else "better", "phrase": ""} for p in payload.topics]
    r["classification_status"] = "classified" if payload.topics else "checked" if payload.checked else "not_sure"
    return store.put("reviews", r, s["user_id"])

@router.get("/dashboard")
def stats(s=Depends(owner)):
    return dashboard(store.records("reviews", s["user_id"]), store.records("plans", s["user_id"]), s["last_seen"])

@router.get("/knowledge")
def knowledge(s=Depends(owner)):
    return {"rules": RULES, "suggestions": SUGGESTIONS}

@router.get("/suggestions")
def suggestions(s=Depends(owner)):
    with store.connect() as db:
        ignored = [r[0] for r in db.execute("SELECT key FROM decisions WHERE user_id=?", (s["user_id"],))]
    return [p for p in patterns(store.records("reviews", s["user_id"])) if p["key"] not in ignored]

class Decision(BaseModel):
    key: str
    ignored: bool = True

@router.post("/suggestions/decision")
def decision(payload: Decision, s=Depends(owner)):
    if payload.key not in SUGGESTIONS:
        raise HTTPException(422, "Unknown suggestion.")
    with store.connect() as db:
        if payload.ignored:
            db.execute("INSERT OR IGNORE INTO decisions VALUES(?,?)", (s["user_id"], payload.key))
        else:
            db.execute("DELETE FROM decisions WHERE user_id=? AND key=?", (s["user_id"], payload.key))
    return {"ok": True}

class PlanPayload(BaseModel):
    key: str
    status: str = "saved"

class PlanUpdate(BaseModel):
    status: str

def valid_status(status):
    if status not in {"saved", "trying", "done", "stopped"}:
        raise HTTPException(422, "Unknown plan status.")

def start_plan(p, rs):
    p.update(baseline(p, rs))
    p["started_at"] = now()

@router.get("/plans")
def plans(s=Depends(owner)):
    rs = store.records("reviews", s["user_id"])
    return [{**p, "progress": progress(p, rs)} for p in store.records("plans", s["user_id"])]

@router.post("/plans", status_code=201)
def create_plan(payload: PlanPayload, s=Depends(owner)):
    valid_status(payload.status)
    rs = store.records("reviews", s["user_id"])
    suggestion = next((p for p in patterns(rs) if p["key"] == payload.key), None)
    if not suggestion:
        raise HTTPException(422, "At least three matching reviews are required for an approved suggestion.")
    existing = next((p for p in store.records("plans", s["user_id"]) if p["key"] == payload.key and p["status"] in {"saved", "trying"}), None)
    if existing:
        return update_plan(existing["id"], PlanUpdate(status=payload.status), s)
    p = {"id": str(uuid4()), "user_id": s["user_id"], "key": payload.key, "topic": suggestion["topic"],
         "title": suggestion["title"], "description": suggestion["suggestion"], "status": payload.status,
         "created_at": now(), "updated_at": now(), "started_at": None}
    if payload.status == "trying":
        start_plan(p, rs)
    return store.put("plans", p, s["user_id"])

@router.patch("/plans/{id}")
def update_plan(id: str, payload: PlanUpdate, s=Depends(owner)):
    valid_status(payload.status)
    p = get_record("plans", id, s["user_id"])
    if payload.status == "trying" and p["status"] != "trying":
        start_plan(p, store.records("reviews", s["user_id"]))
    p.update(status=payload.status, updated_at=now())
    return store.put("plans", p, s["user_id"])

@router.delete("/plans/{id}")
def delete_plan(id: str, s=Depends(owner)):
    get_record("plans", id, s["user_id"])
    with store.connect() as db:
        db.execute("DELETE FROM plans WHERE id=? AND user_id=?", (id, s["user_id"]))
    return {"ok": True}

@router.get("/performance/monthly")
def performance(month: str = "", s=Depends(owner)):
    month = month or date.today().strftime("%Y-%m")
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(422, "Month must be YYYY-MM.")
    return monthly(month, store.records("reviews", s["user_id"]), store.records("plans", s["user_id"]))
