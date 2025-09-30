"""Unit tests for indexer decoder stub (Phase 4)."""

from web3 import Web3

from src.services.indexers.avantis_indexer import _decode_event


class TestDecoderStub:
    """Test decoder stub returns empty list."""

    def test_decoder_returns_list(self) -> None:
        """Test that decoder returns a list (even if empty)."""
        w3 = Web3()
        result = _decode_event(w3, {})
        assert isinstance(result, list)
        assert len(result) == 0  # Stub returns empty list
