"""Prometheus metrics (Phase 8)."""

from prometheus_client import Counter, Gauge, Histogram

# Webhook metrics
signals_queued = Counter(
    "vanta_signals_queued_total", "Signals accepted and queued", ["source"]
)
signals_rejected = Counter(
    "vanta_signals_rejected_total", "Signals rejected", ["reason"]
)

# Worker metrics
exec_processed = Counter(
    "vanta_exec_processed_total", "Executions processed", ["status"]
)
exec_latency = Histogram("vanta_worker_exec_latency_seconds", "Signal->send latency")

# Queue metrics
queue_depth = Gauge("vanta_signals_queue_depth", "Current Redis queue length")

# TP/SL metrics
tpsl_triggers = Counter(
    "vanta_tpsl_triggers_total", "TP/SL triggers executed", ["type"]
)  # type: TP|SL
tpsl_errors = Counter("vanta_tpsl_errors_total", "TP/SL executor errors")

# Bot metrics
bot_tx_sent = Counter(
    "vanta_bot_tx_sent_total", "Bot-initiated transactions", ["action"]
)  # open|close
bot_errors = Counter("vanta_bot_errors_total", "Bot handler errors")

# Generic health
loop_heartbeat = Gauge("vanta_loop_heartbeat", "1 when loop healthy", ["component"])
