"""Run webhook API server (Phase 6)."""

import logging

import uvicorn

from src.api.webhook import app

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    uvicorn.run(app, host="0.0.0.0", port=8090)
