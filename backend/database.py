"""SQLite persistence for TrustMesh AI decisions (audit trail)."""

import datetime as dt
import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./trustmesh.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    phone_number = Column(String, index=True)
    transaction_type = Column(String)
    trust_score = Column(Float)
    decision = Column(String)  # APPROVE | CHALLENGE | BLOCK
    signals_json = Column(Text)  # raw signals fetched from NaC
    reasoning = Column(Text)  # explanation produced by the agent

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "phone_number": self.phone_number,
            "transaction_type": self.transaction_type,
            "trust_score": self.trust_score,
            "decision": self.decision,
            "signals": json.loads(self.signals_json) if self.signals_json else {},
            "reasoning": self.reasoning,
        }


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
