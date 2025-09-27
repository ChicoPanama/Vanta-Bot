"""
Unit tests for Avantis SDK DTO mapping and execution modes

This module tests the DTO mapping between bot orders and SDK TradeInput,
and verifies execution mode behavior.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from src.services.trading.avantis_executor import OrderRequest, AvantisExecutor, get_execution_mode, set_execution_mode
from src.services.markets.avantis_price_provider import AvantisPriceProvider


class TestOrderRequest:
    """Test OrderRequest data structure"""
    
    def test_order_request_creation(self):
        """Test creating an OrderRequest"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market",
            slippage_pct=1.0
        )
        
        assert order.pair == "ETH/USD"
        assert order.is_long is True
        assert order.collateral_usdc == 100.0
        assert order.leverage == 10.0
        assert order.order_type == "market"
        assert order.slippage_pct == 1.0
        assert order.limit_price is None
        assert order.tp is None
        assert order.sl is None
    
    def test_order_request_defaults(self):
        """Test OrderRequest with default values"""
        order = OrderRequest(
            pair="BTC/USD",
            is_long=False,
            collateral_usdc=50.0,
            leverage=5.0
        )
        
        assert order.pair == "BTC/USD"
        assert order.is_long is False
        assert order.collateral_usdc == 50.0
        assert order.leverage == 5.0
        assert order.order_type == "market"
        assert order.slippage_pct == 0.5


class TestAvantisExecutor:
    """Test AvantisExecutor class and DTO mapping"""
    
    @pytest.fixture
    def executor(self):
        """Create an AvantisExecutor instance for testing"""
        return AvantisExecutor()
    
    def test_build_trade_input_snake_case(self, executor):
        """Test building TradeInput with snake_case fields"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market",
            slippage_pct=1.0
        )
        
        trader_address = "0x1234567890123456789012345678901234567890"
        pair_index = 1
        
        trade_input = executor._build_trade_input(order, trader_address, pair_index)
        
        # Verify snake_case field names as per Avantis SDK
        assert trade_input.trader == trader_address
        assert trade_input.open_price is None  # Market order
        assert trade_input.pair_index == pair_index
        assert trade_input.collateral_in_trade == 100.0
        assert trade_input.is_long is True
        assert trade_input.leverage == 10.0
        assert trade_input.index == 0
        assert trade_input.tp == 0
        assert trade_input.sl == 0
        assert trade_input.timestamp == 0
    
    def test_get_order_type_market(self, executor):
        """Test getting order type for market orders"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market"
        )
        
        order_type = executor._get_order_type(order, zero_fee=False)
        # This would be TradeInputOrderType.MARKET in real implementation
        assert order_type is not None
    
    def test_get_order_type_market_zero_fee(self, executor):
        """Test getting order type for market zero fee orders"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market"
        )
        
        order_type = executor._get_order_type(order, zero_fee=True)
        # This would be TradeInputOrderType.MARKET_ZERO_FEE in real implementation
        assert order_type is not None
    
    def test_get_order_type_limit(self, executor):
        """Test getting order type for limit orders"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="limit"
        )
        
        order_type = executor._get_order_type(order, zero_fee=False)
        # This would be TradeInputOrderType.LIMIT in real implementation
        assert order_type is not None
    
    @pytest.mark.asyncio
    async def test_open_market_dry_mode(self, executor):
        """Test open_market in DRY mode returns DRYRUN"""
        # Set execution mode to DRY
        set_execution_mode("DRY")
        
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market"
        )
        
        with patch.object(executor, '_get_sdk_client') as mock_get_client, \
             patch.object(executor, '_get_price_provider') as mock_get_provider:
            
            mock_client = Mock()
            mock_client.get_trader_address.return_value = "0x1234567890123456789012345678901234567890"
            mock_get_client.return_value = mock_client
            
            mock_provider = Mock()
            mock_provider.get_pair_index = AsyncMock(return_value=1)
            mock_provider.quote_open = AsyncMock(return_value={
                "pair_index": 1,
                "position_size": 1000.0,
                "opening_fee_usdc": 2.5,
                "loss_protection_percent": 5.0,
                "loss_protection_amount": 50.0,
                "impact_spread": 0.1,
                "slippage_pct": 1.0
            })
            mock_get_provider.return_value = mock_provider
            
            result = await executor.open_market(order)
            
            assert result.success is True
            assert result.tx_hash == "DRYRUN"
            assert result.quote is not None
    
    @pytest.mark.asyncio
    async def test_open_market_live_mode_calls_sdk(self, executor):
        """Test open_market in LIVE mode calls SDK methods"""
        # Set execution mode to LIVE
        set_execution_mode("LIVE")
        
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market"
        )
        
        with patch.object(executor, '_get_sdk_client') as mock_get_client, \
             patch.object(executor, '_get_price_provider') as mock_get_provider, \
             patch('src.services.trading.avantis_executor.get_sdk_client') as mock_sdk_client:
            
            mock_client = Mock()
            mock_client.get_trader_address.return_value = "0x1234567890123456789012345678901234567890"
            mock_client.trade.build_trade_open_tx = AsyncMock(return_value="mock_tx")
            mock_client.sign_and_get_receipt = AsyncMock(return_value="0x1234567890abcdef")
            mock_get_client.return_value = mock_client
            
            mock_provider = Mock()
            mock_provider.get_pair_index = AsyncMock(return_value=1)
            mock_provider.quote_open = AsyncMock(return_value={
                "pair_index": 1,
                "position_size": 1000.0,
                "opening_fee_usdc": 2.5,
                "loss_protection_percent": 5.0,
                "loss_protection_amount": 50.0,
                "impact_spread": 0.1,
                "slippage_pct": 1.0
            })
            mock_get_provider.return_value = mock_provider
            
            mock_sdk_client.return_value.ensure_usdc_allowance = AsyncMock(return_value=True)
            
            result = await executor.open_market(order)
            
            # Verify SDK methods were called in LIVE mode
            mock_client.trade.build_trade_open_tx.assert_called_once()
            mock_client.sign_and_get_receipt.assert_called_once()
            mock_sdk_client.return_value.ensure_usdc_allowance.assert_called_once()
            
            assert result.success is True
            assert result.tx_hash == "0x1234567890abcdef"


class TestExecutionMode:
    """Test execution mode functionality"""
    
    def test_get_execution_mode(self):
        """Test getting current execution mode"""
        mode = get_execution_mode()
        assert mode in ["DRY", "LIVE"]
    
    def test_set_execution_mode_valid(self):
        """Test setting valid execution mode"""
        # Test setting DRY mode
        success = set_execution_mode("DRY")
        assert success is True
        assert get_execution_mode() == "DRY"
        
        # Test setting LIVE mode
        success = set_execution_mode("LIVE")
        assert success is True
        assert get_execution_mode() == "LIVE"
    
    def test_set_execution_mode_invalid(self):
        """Test setting invalid execution mode"""
        success = set_execution_mode("INVALID")
        assert success is False
    
    def test_set_execution_mode_case_insensitive(self):
        """Test that execution mode is case insensitive"""
        success = set_execution_mode("dry")
        assert success is True
        assert get_execution_mode() == "DRY"
        
        success = set_execution_mode("live")
        assert success is True
        assert get_execution_mode() == "LIVE"


class TestAvantisPriceProvider:
    """Test AvantisPriceProvider class"""
    
    @pytest.fixture
    def price_provider(self):
        """Create an AvantisPriceProvider instance for testing"""
        return AvantisPriceProvider()
    
    @pytest.mark.asyncio
    async def test_quote_open_returns_dict(self, price_provider):
        """Test that quote_open returns a dictionary"""
        with patch.object(price_provider, 'get_pair_index', return_value=1) as mock_pair_index, \
             patch.object(price_provider, 'estimate_opening_fee', return_value=2.5) as mock_fee, \
             patch.object(price_provider, 'get_loss_protection') as mock_loss_protection, \
             patch.object(price_provider, 'get_pair_spread', return_value=None) as mock_spread, \
             patch.object(price_provider, 'get_price_impact_spread', return_value=0.1) as mock_price_impact, \
             patch.object(price_provider, 'get_skew_impact_spread', return_value=0.05) as mock_skew_impact:
            
            # Mock loss protection response
            loss_protection = Mock()
            loss_protection.loss_protection_percent = 5.0
            loss_protection.loss_protection_amount = 50.0
            mock_loss_protection.return_value = loss_protection
            
            quote = await price_provider.quote_open(
                pair="ETH/USD",
                is_long=True,
                collateral_usdc=100.0,
                leverage=10.0,
                slippage_pct=1.0
            )
            
            assert isinstance(quote, dict)
            assert quote["pair_index"] == 1
            assert quote["position_size"] == 1000.0  # 100 * 10
            assert quote["opening_fee_usdc"] == 2.5
            assert quote["loss_protection_percent"] == 5.0
            assert quote["loss_protection_amount"] == 50.0
            assert quote["impact_spread"] == 0.1
            assert quote["slippage_pct"] == 1.0


class TestIntegration:
    """Integration tests for the Avantis SDK components"""
    
    @pytest.mark.asyncio
    async def test_order_request_to_trade_input_flow(self):
        """Test the flow from OrderRequest to TradeInput"""
        # Create an order request
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market",
            slippage_pct=1.0
        )
        
        # Create executor and build trade input
        executor = AvantisExecutor()
        trader_address = "0x1234567890123456789012345678901234567890"
        pair_index = 1
        
        trade_input = executor._build_trade_input(order, trader_address, pair_index)
        
        # Verify the trade input is correctly built
        assert trade_input.trader == trader_address
        assert trade_input.open_price is None  # Market order
        assert trade_input.pair_index == pair_index
        assert trade_input.collateral_in_trade == 100.0
        assert trade_input.is_long is True
        assert trade_input.leverage == 10.0
    
    @pytest.mark.asyncio
    async def test_execution_mode_affects_behavior(self):
        """Test that execution mode affects trade execution behavior"""
        # Test DRY mode
        set_execution_mode("DRY")
        
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0
        )
        
        executor = AvantisExecutor()
        
        with patch.object(executor, '_get_sdk_client') as mock_get_client, \
             patch.object(executor, '_get_price_provider') as mock_get_provider:
            
            mock_client = Mock()
            mock_client.get_trader_address.return_value = "0x1234567890123456789012345678901234567890"
            mock_get_client.return_value = mock_client
            
            mock_provider = Mock()
            mock_provider.get_pair_index = AsyncMock(return_value=1)
            mock_provider.quote_open = AsyncMock(return_value={
                "pair_index": 1,
                "position_size": 1000.0,
                "opening_fee_usdc": 2.5,
                "loss_protection_percent": 5.0,
                "loss_protection_amount": 50.0,
                "impact_spread": 0.1,
                "slippage_pct": 1.0
            })
            mock_get_provider.return_value = mock_provider
            
            result = await executor.open_market(order)
            
            # In DRY mode, should not call SDK execution methods
            assert result.tx_hash == "DRYRUN"
            assert result.success is True


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
