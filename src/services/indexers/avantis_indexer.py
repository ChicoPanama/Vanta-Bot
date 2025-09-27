# src/services/indexers/avantis_indexer.py
from __future__ import annotations
import asyncio, json, os, time
from dataclasses import dataclass
from typing import Optional, Iterable, Dict, Any, List, Tuple
from decimal import Decimal

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from web3 import Web3
from web3.providers.websocket import WebsocketProviderV2
from web3.providers.rpc import HTTPProvider
from web3.contract.contract import Contract
from web3.types import LogReceipt
from sqlalchemy.orm import Session

# === ENV / CONFIG ===
BASE_RPC_URL = os.getenv("BASE_RPC_URL")
BASE_WS_URL = os.getenv("BASE_WS_URL", "")
BASE_CHAIN_ID = int(os.getenv("BASE_CHAIN_ID", "8453"))
AVANTIS_TRADING_CONTRACT = os.getenv("AVANTIS_TRADING_CONTRACT")  # 0x...
AVANTIS_VAULT_CONTRACT = os.getenv("AVANTIS_VAULT_CONTRACT")      # 0x...
USDC_CONTRACT = os.getenv("USDC_CONTRACT")                        # present in env.example

ABI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "config", "abis")
TRADING_ABI_PATH = os.path.join(ABI_DIR, "Trading.json")
VAULT_ABI_PATH = os.path.join(ABI_DIR, "Vault.json")

# === SIMPLE DTOs ===
@dataclass
class TraderFill:
    address: str
    pair: str
    is_long: bool
    size: float
    price: float
    fee: float
    side: str           # "OPEN" | "CLOSE" | "LIMIT" | "LIQUIDATION"
    block_number: int
    tx_hash: str
    ts: int
    maker_taker: Optional[str] = None

@dataclass
class TraderPosition:
    address: str
    pair: str
    entry_px: float
    size: float
    is_long: bool
    opened_at: int
    closed_at: Optional[int]
    pnl_realized: float
    fees: float
    funding: float
    tx_open: str
    tx_close: Optional[str]

def _load_abi(path: str) -> List[Dict[str, Any]]:
    """Load ABI from JSON file with fallback"""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"ABI file not found: {path}. Using empty ABI.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in ABI file {path}: {e}")
        return []

class AvantisIndexer:
    """
    First-pass Avantis indexer:
    - Uses HTTP provider for backfill (reliable pagination).
    - Uses WS provider for tailing (low-latency new blocks).
    - Decodes Trading/Vault events with local ABIs (put ABI JSON in config/abis).
    - Writes out normalized events via user-provided callbacks (inject later).
    - Persists fills directly to database for real-time analytics.
    """
    def __init__(self) -> None:
        if not BASE_RPC_URL or not AVANTIS_TRADING_CONTRACT:
            raise RuntimeError("Missing BASE_RPC_URL or AVANTIS_TRADING_CONTRACT in environment.")
        
        self.w3_http = Web3(HTTPProvider(BASE_RPC_URL, request_kwargs={"timeout": 30}))
        self.w3_ws: Optional[Web3] = None
        
        if BASE_WS_URL:
            try:
                self.w3_ws = Web3(WebsocketProviderV2(BASE_WS_URL))
            except Exception as e:
                logger.warning(f"Failed to initialize WebSocket provider: {e}")
        
        # Load ABIs with fallback
        self.trading_abi = _load_abi(TRADING_ABI_PATH)
        self.vault_abi = _load_abi(VAULT_ABI_PATH)

        # Initialize contracts
        self.trading: Contract = self.w3_http.eth.contract(
            address=Web3.to_checksum_address(AVANTIS_TRADING_CONTRACT),
            abi=self.trading_abi,
        )
        
        self.vault: Optional[Contract] = None
        if AVANTIS_VAULT_CONTRACT and self.vault_abi:
            self.vault = self.w3_http.eth.contract(
                address=Web3.to_checksum_address(AVANTIS_VAULT_CONTRACT),
                abi=self.vault_abi,
            )

        # Database session factory for persistence
        self._session_factory = None
        
        # Placeholders for persistence callbacks (wire to your DB layer)
        self.on_fill = None        # Callable[[TraderFill], Awaitable[None]]
        self.on_position = None    # Callable[[TraderPosition], Awaitable[None]]
        
        logger.info("AvantisIndexer initialized (chain_id={}, http={}, ws={})",
                    BASE_CHAIN_ID, bool(self.w3_http), bool(self.w3_ws))

    # ---- Public API ----
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def backfill(self, from_block: int, to_block: int) -> int:
        """
        Backfills Trading contract events between blocks. This is a thin skeleton; you will map
        concrete ABI event names here once your Trading.json is present.
        """
        logger.info("Backfill start: {} -> {}", from_block, to_block)
        
        # Example: if Trading.json defines events 'TradeOpened', 'TradeClosed', 'LimitExecuted', 'Liquidation'
        # you can filter like this:
        event_names = ["TradeOpened", "TradeClosed", "LimitExecuted", "Liquidation"]
        total = 0
        
        for name in event_names:
            if not hasattr(self.trading.events, name):
                logger.warning("ABI does not contain event {}", name)
                continue
                
            event_cls = getattr(self.trading.events, name)
            # Paginate by 2k blocks for safety
            step = 2000
            
            for start in range(from_block, to_block + 1, step):
                end = min(start + step - 1, to_block)
                try:
                    logs: Iterable[LogReceipt] = event_cls().get_logs(fromBlock=start, toBlock=end)
                except Exception as e:
                    logger.exception("get_logs failed {} {}-{}: {}", name, start, end, e)
                    raise
                    
                for log in logs:
                    await self._consume_event(name, log)
                    total += 1
                    
        logger.info("Backfill complete. events={}", total)
        return total

    async def tail_follow(self, start_block: Optional[int] = None) -> None:
        """
        Subscribe new blocks (WS if available; else poll HTTP) and process Trading events forward.
        """
        logger.info("Tail follow starting (ws={})", bool(self.w3_ws))
        current = start_block or self.w3_http.eth.block_number
        
        while True:
            try:
                latest = (self.w3_http.eth.block_number
                          if not self.w3_ws else self.w3_ws.eth.block_number)
                          
                if latest > current:
                    await self.backfill(current + 1, latest)
                    current = latest
                    
                await asyncio.sleep(2 if self.w3_ws else 5)
            except Exception as e:
                logger.exception("tail_follow loop error: {}", e)
                await asyncio.sleep(5)

    # ---- Internal decoding ----
    async def _consume_event(self, name: str, log: LogReceipt) -> None:
        """
        Decode an event into our normalized DTOs and forward to persistence callbacks.
        The exact field names depend on Trading.json; fill mapping once ABI is in place.
        """
        try:
            data = dict(log["args"]) if "args" in log and isinstance(log["args"], dict) else {}
        except Exception:
            data = {}
            
        block_number = log.get("blockNumber", 0) or 0
        tx_hash = log.get("transactionHash", b"").hex()

        # Map event name to side based on ABI inspection
        name_upper = name.upper()
        if name_upper in ("TRADEOPENED", "LIMITEXECUTED"):
            side = "OPEN"
        elif name_upper in ("TRADECLOSED", "LIQUIDATION"):
            side = "CLOSE"
        else:
            side = name_upper

        # Extract fields based on actual ABI structure from Trading.json
        address = str(data.get("trader", ""))
        pair = str(data.get("pair", ""))
        
        # Handle is_long field (only present in TradeOpened)
        is_long = data.get("isLong", False) if "isLong" in data else False
        
        size = float(data.get("size", 0))
        price = float(data.get("price", 0))
        fee = float(data.get("fee", 0))
        
        # Additional fields for specific events
        pnl = float(data.get("pnl", 0)) if "pnl" in data else 0
        loss = float(data.get("loss", 0)) if "loss" in data else 0
        ts = await self._block_timestamp(block_number)

        # Calculate notional USD value
        notional = Decimal(abs(price * size))
        block_hash = log.get("blockHash", b"").hex() if log.get("blockHash") else None

        # Persist to database if session factory is available
        if self._session_factory:
            try:
                # Import here to avoid circular imports
                from src.database.models.trading import Fill
                from sqlalchemy import text
                
                with self._session_factory() as session:  # type: Session
                    # Check for duplicate
                    existing = session.execute(
                        text("SELECT id FROM fills WHERE tx_hash = :tx_hash AND address = :address AND pair = :pair AND side = :side"),
                        {
                            "tx_hash": tx_hash,
                            "address": address.lower(),
                            "pair": pair,
                            "side": side
                        }
                    ).fetchone()
                    
                    if not existing:
                        fill_record = Fill(
                            address=address.lower(),
                            pair=pair,
                            is_long=is_long,
                            size=str(size),
                            price=str(price),
                            notional_usd=str(notional),
                            fee=str(fee),
                            side=side,
                            maker_taker=None,  # Not available in current ABI
                            block_number=block_number,
                            block_hash=block_hash,
                            tx_hash=tx_hash,
                            ts=ts
                        )
                        session.add(fill_record)
                        session.commit()
                        logger.debug(f"Persisted fill: {address[:8]}... {pair} {side}")
                    else:
                        logger.debug(f"Duplicate fill skipped: {tx_hash}")
                        
            except Exception as e:
                logger.error(f"Failed to persist fill: {e}")

        # Create normalized fill for callbacks
        fill = TraderFill(
            address=address, pair=pair, is_long=is_long, size=size, price=price,
            fee=fee, side=side, block_number=block_number, tx_hash=tx_hash, ts=ts
        )
        
        if self.on_fill:
            await self.on_fill(fill)

        # Log event for debugging
        logger.debug(f"Processed {name} event: {address[:8]}... {pair} {side} size={size} price={price}")

        return

    async def _block_timestamp(self, block_number: int) -> int:
        """Get block timestamp with fallback"""
        try:
            blk = self.w3_http.eth.get_block(block_number)
            return int(blk["timestamp"])
        except Exception:
            return int(time.time())

    def set_callbacks(self, on_fill=None, on_position=None):
        """Set persistence callbacks"""
        if on_fill:
            self.on_fill = on_fill
        if on_position:
            self.on_position = on_position

    def set_db_session_factory(self, session_factory):
        """Set database session factory for persistence"""
        self._session_factory = session_factory
        logger.info("Database session factory set for persistence")
