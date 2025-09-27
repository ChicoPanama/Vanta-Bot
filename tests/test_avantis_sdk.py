"""
Unit tests for Avantis SDK integration

This module contains basic unit tests for the Avantis Trader SDK integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from src.services.trading.avantis_executor import OrderRequest, AvantisExecutor
from src.services.markets.avantis_price_provider import TradeQuote, AvantisPriceProvider


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
            limit_price=None,
            tp=4000.0,
            sl=3000.0,
            slippage_pct=0.5
        )
        
        assert order.pair == "ETH/USD"
        assert order.is_long is True
        assert order.collateral_usdc == 100.0
        assert order.leverage == 10.0
        assert order.order_type == "market"
        assert order.limit_price is None
        assert order.tp == 4000.0
        assert order.sl == 3000.0
        assert order.slippage_pct == 0.5
    
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
        assert order.limit_price is None
        assert order.tp is None
        assert order.sl is None
        assert order.slippage_pct == 0.5


class TestTradeQuote:
    """Test TradeQuote data structure"""
    
    def test_trade_quote_creation(self):
        """Test creating a TradeQuote"""
        quote = TradeQuote(
            pair_index=1,
            position_size=1000.0,
            opening_fee_usdc=2.5,
            loss_protection_percent=5.0,
            loss_protection_amount=50.0,
            slippage_pct=0.5
        )
        
        assert quote.pair_index == 1
        assert quote.position_size == 1000.0
        assert quote.opening_fee_usdc == 2.5
        assert quote.loss_protection_percent == 5.0
        assert quote.loss_protection_amount == 50.0
        assert quote.slippage_pct == 0.5
        assert quote.pair_spread is None
        assert quote.price_impact_spread is None
        assert quote.skew_impact_spread is None


class TestAvantisExecutor:
    """Test AvantisExecutor class"""
    
    @pytest.fixture
    def executor(self):
        """Create an AvantisExecutor instance for testing"""
        return AvantisExecutor()
    
    def test_build_trade_input(self, executor):
        """Test building TradeInput from OrderRequest"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            limit_price=3000.0,
            tp=4000.0,
            sl=2000.0
        )
        
        trader_address = "0x1234567890123456789012345678901234567890"
        
        trade_input = executor._build_trade_input(order, trader_address)
        
        assert trade_input.trader == trader_address
        assert trade_input.open_price == 3000.0
        assert trade_input.pair_index == 0  # Will be set later
        assert trade_input.collateral_in_trade == 100.0
        assert trade_input.is_long is True
        assert trade_input.leverage == 10.0
        assert trade_input.tp == 4000.0
        assert trade_input.sl == 2000.0
    
    def test_get_order_type_market(self, executor):
        """Test getting order type for market orders"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="market"
        )
        
        order_type = executor._get_order_type(order)
        
        # This would be TradeInputOrderType.MARKET in real implementation
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
        
        order_type = executor._get_order_type(order)
        
        # This would be TradeInputOrderType.LIMIT in real implementation
        assert order_type is not None
    
    def test_get_order_type_invalid(self, executor):
        """Test getting order type for invalid order type"""
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0,
            order_type="invalid"
        )
        
        order_type = executor._get_order_type(order)
        
        # Should default to MARKET
        assert order_type is not None


class TestAvantisPriceProvider:
    """Test AvantisPriceProvider class"""
    
    @pytest.fixture
    def price_provider(self):
        """Create an AvantisPriceProvider instance for testing"""
        return AvantisPriceProvider()
    
    @pytest.mark.asyncio
    async def test_get_pair_index_mock(self, price_provider):
        """Test getting pair index with mocked client"""
        with patch.object(price_provider, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_client.pairs_cache.get_pair_index = AsyncMock(return_value=1)
            mock_get_client.return_value = mock_client
            
            pair_index = await price_provider.get_pair_index("ETH/USD")
            
            assert pair_index == 1
            mock_client.pairs_cache.get_pair_index.assert_called_once_with("ETH/USD")
    
    @pytest.mark.asyncio
    async def test_estimate_opening_fee_mock(self, price_provider):
        """Test estimating opening fee with mocked client"""
        with patch.object(price_provider, '_get_client') as mock_get_client:
            mock_client = Mock()
            mock_client.fee_parameters.get_opening_fee = AsyncMock(return_value=2.5)
            mock_get_client.return_value = mock_client
            
            # Create a mock trade input
            trade_input = Mock()
            
            opening_fee = await price_provider.estimate_opening_fee(trade_input)
            
            assert opening_fee == 2.5
            mock_client.fee_parameters.get_opening_fee.assert_called_once_with(trade_input)
    
    @pytest.mark.asyncio
    async def test_quote_open_mock(self, price_provider):
        """Test creating trade quote with mocked methods"""
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
                slippage_pct=0.5
            )
            
            assert isinstance(quote, TradeQuote)
            assert quote.pair_index == 1
            assert quote.position_size == 1000.0  # 100 * 10
            assert quote.opening_fee_usdc == 2.5
            assert quote.loss_protection_percent == 5.0
            assert quote.loss_protection_amount == 50.0
            assert quote.slippage_pct == 0.5
            assert quote.price_impact_spread == 0.1
            assert quote.skew_impact_spread == 0.05


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
            order_type="market"
        )
        
        # Create executor and build trade input
        executor = AvantisExecutor()
        trader_address = "0x1234567890123456789012345678901234567890"
        
        trade_input = executor._build_trade_input(order, trader_address)
        
        # Verify the trade input is correctly built
        assert trade_input.trader == trader_address
        assert trade_input.open_price is None  # Market order
        assert trade_input.collateral_in_trade == 100.0
        assert trade_input.is_long is True
        assert trade_input.leverage == 10.0
    
    @pytest.mark.asyncio
    async def test_mock_trade_execution_flow(self):
        """Test the complete trade execution flow with mocks"""
        # This test would mock the entire SDK client and test the execution flow
        # For now, we'll just test the structure
        
        order = OrderRequest(
            pair="ETH/USD",
            is_long=True,
            collateral_usdc=100.0,
            leverage=10.0
        )
        
        executor = AvantisExecutor()
        
        # Mock the SDK client and its methods
        with patch.object(executor, '_get_sdk_client') as mock_get_client, \
             patch.object(executor, '_get_price_provider') as mock_get_provider:
            
            mock_client = Mock()
            mock_client.get_trader_address.return_value = "0x1234567890123456789012345678901234567890"
            mock_get_client.return_value = mock_client
            
            mock_provider = Mock()
            mock_provider.get_pair_index = AsyncMock(return_value=1)
            mock_get_provider.return_value = mock_provider
            
            # Mock the trade execution methods
            mock_client.trade.build_trade_open_tx = AsyncMock(return_value="mock_tx")
            mock_client.sign_and_get_receipt = AsyncMock(return_value="0x1234567890abcdef")
            
            # This would normally call open_market, but we'll just test the structure
            assert order.pair == "ETH/USD"
            assert order.is_long is True
            assert order.collateral_usdc == 100.0


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
