"""Webhook API for signal ingestion (Phase 6)."""

import hashlib
import hmac
import json
import logging

import redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.schemas import SignalIn
from src.config.settings import settings
from src.repositories.signals_repo import create_execution, upsert_signal

logger = logging.getLogger(__name__)

app = FastAPI(title="Vanta-Bot Signals API")

# Lazy DB factory
_eng = None
_Session = None


def _get_session():
    """Get database session factory."""
    global _eng, _Session
    if _Session is None:
        db_url = settings.DATABASE_URL.replace("sqlite+aiosqlite:", "sqlite:")
        _eng = create_engine(db_url, pool_pre_ping=True)
        _Session = sessionmaker(bind=_eng, expire_on_commit=False)
    return _Session()


def _verify_hmac(req_body: bytes, signature: str | None) -> bool:
    """Verify HMAC signature.

    Args:
        req_body: Request body bytes
        signature: Signature from X-Signature header

    Returns:
        True if valid or HMAC not configured
    """
    if not settings.WEBHOOK_HMAC_SECRET:
        logger.warning("HMAC secret not configured - accepting all requests (dev only)")
        return True  # dev only

    if not signature:
        return False

    mac = hmac.new(
        settings.WEBHOOK_HMAC_SECRET.encode(),
        msg=req_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(mac, signature)


def _get_queue():
    """Get Redis queue client."""
    return redis.from_url(settings.REDIS_URL)


@app.post("/signals")
async def receive_signal(req: Request):
    """Receive and queue trade signal.

    Args:
        req: FastAPI request

    Returns:
        JSON response with status and intent_key
    """
    body = await req.body()
    sig = req.headers.get("X-Signature")

    if not _verify_hmac(body, sig):
        logger.warning("Invalid HMAC signature")
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data = SignalIn(**json.loads(body.decode()))
    except Exception as e:
        logger.error(f"Invalid signal payload: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Build intent key — unique idempotency key
    intent_key = f"sig:{data.source}:{data.signal_id}"

    # Persist signal & create execution row
    db = _get_session()
    try:
        upsert_signal(
            db,
            source=data.source,
            signal_id=data.signal_id,
            intent_key=intent_key,
            payload=data.model_dump(),
        )
        create_execution(db, intent_key, status="QUEUED")
    finally:
        db.close()

    # Push to queue (RPUSH)
    _get_queue().rpush(settings.SIGNALS_QUEUE, json.dumps({"intent_key": intent_key}))

    logger.info(
        f"Signal queued: {intent_key} | source={data.source} | user={data.tg_user_id}"
    )
    return JSONResponse({"status": "queued", "intent_key": intent_key})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "vanta-bot-signals"}
