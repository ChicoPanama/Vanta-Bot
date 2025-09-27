import aiohttp
import asyncio
from typing import Dict
import logging

logger = logging.getLogger(__name__)

class PriceService:
    def __init__(self):
        self.prices = {}
        self.update_interval = 5  # seconds
        
    async def fetch_prices(self):
        """Fetch prices from CoinGecko API"""
        try:
            # FIX: Add timeout to prevent hanging connections
            # REASON: ClientSession without timeout can hang indefinitely
            # REVIEW: Line 16 from code review - aiohttp.ClientSession without timeout
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Crypto prices
                crypto_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"
                async with session.get(crypto_url) as response:
                    crypto_data = await response.json()
                    
                # Update prices
                self.prices.update({
                    'BTC': crypto_data.get('bitcoin', {}).get('usd', 0),
                    'ETH': crypto_data.get('ethereum', {}).get('usd', 0),
                    'SOL': crypto_data.get('solana', {}).get('usd', 0)
                })
                
                # For forex, you'd use a forex API
                # For now, using mock data
                self.prices.update({
                    'EURUSD': 1.0850,
                    'GBPUSD': 1.2650,
                    'USDJPY': 149.50
                })
                
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            
    async def start_price_updates(self):
        """Start continuous price updates"""
        while True:
            await self.fetch_prices()
            await asyncio.sleep(self.update_interval)
            
    def get_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        return self.prices.get(symbol, 0.0)

# Global instance
price_service = PriceService()
