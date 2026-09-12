import json
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agent import evaluate_transaction
from database import Decision, get_session, init_db

app = FastAPI(title="TrustMesh AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class TransactionRequest(BaseModel):
    phone_number: str
    transaction_type: str = "login"
    claimed_latitude: Optional[float] = None
    claimed_longitude: Optional[float] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/evaluate-transaction")
def evaluate(req: TransactionRequest, db: Session = Depends(get_session)):
    result = evaluate_transaction(
        phone_number=req.phone_number,
        transaction_type=req.transaction_type,
        claimed_latitude=req.claimed_latitude,
        claimed_longitude=req.claimed_longitude,
    )

    record = Decision(
        phone_number=req.phone_number,
        transaction_type=req.transaction_type,
        trust_score=result["trust_score"],
        decision=result["decision"],
        signals_json=json.dumps(result["signals"]),
        reasoning=result["reasoning"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record.to_dict()


@app.get("/decisions")
def list_decisions(db: Session = Depends(get_session)):
    records = db.query(Decision).order_by(Decision.id.desc()).limit(50).all()
    return [r.to_dict() for r in records]
