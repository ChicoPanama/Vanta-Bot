"""Tests for UI formatting utilities (Phase 5)."""

from src.bot.ui.formatting import code, fmt_addr, h1, ok, usdc1e6, warn


class TestFormatting:
    """Test formatting functions."""

    def test_fmt_addr(self) -> None:
        """Test address formatting."""
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        formatted = fmt_addr(addr)
        assert formatted.startswith("0x1234")
        assert formatted.endswith("5678")
        assert "…" in formatted

    def test_fmt_addr_none(self) -> None:
        """Test address formatting with None."""
        assert fmt_addr(None) == "—"

    def test_usdc1e6(self) -> None:
        """Test USDC formatting."""
        assert usdc1e6(2_500_000) == "2.50 USDC"
        assert usdc1e6(1_000_000) == "1.00 USDC"
        assert usdc1e6(0) == "0.00 USDC"

    def test_h1(self) -> None:
        """Test header formatting."""
        assert h1("Test") == "*Test*"

    def test_code(self) -> None:
        """Test code formatting."""
        assert code("BTC-USD") == "`BTC-USD`"

    def test_ok(self) -> None:
        """Test success formatting."""
        assert ok("Done") == "✅ Done"

    def test_warn(self) -> None:
        """Test warning formatting."""
        assert warn("Error") == "⚠️ Error"
