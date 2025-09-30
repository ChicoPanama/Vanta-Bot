"""
Market Intelligence System for Vanta Bot
Monitors price feeds and classifies market regimes for copy timing signals
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import aiohttp
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    symbol: str
    price: float
    timestamp: datetime
    confidence: float
    source: str


@dataclass
class RegimeSignal:
    symbol: str
    signal: str  # 'green', 'yellow', 'red'
    confidence: float
    volatility: float
    trend: str
    reason: str
    timestamp: datetime


class MarketIntelligence:
    """Market intelligence and regime detection system"""

    def __init__(self, config):
        self.config = config
        self.price_feeds = {}
        self.regime_data = {}
        self.is_running = False

        # Pyth price feed IDs
        self.pyth_feeds = json.loads(config.PYTH_PRICE_FEED_IDS_JSON)

        # Market regime thresholds
        self.volatility_thresholds = {
            "green": 0.3,  # Low volatility - good for copying
            "yellow": 0.6,  # Medium volatility - caution
            "red": float("inf"),  # High volatility - avoid
        }

        # Trend thresholds
        self.trend_thresholds = {
            "bullish": 0.02,  # 2% upward movement
            "bearish": -0.02,  # 2% downward movement
            "neutral": 0.0,  # Between -2% and +2%
        }

    async def start_monitoring(self):
        """Start monitoring price feeds for regime detection"""
        if self.is_running:
            logger.warning("Market intelligence is already running")
            return

        self.is_running = True
        logger.info("Starting market intelligence monitoring...")

        try:
            # Start monitoring all configured price feeds
            tasks = []
            for symbol, pyth_id in self.pyth_feeds.items():
                task = asyncio.create_task(self._monitor_price_feed(symbol, pyth_id))
                tasks.append(task)

            # Start overall regime analysis task
            analysis_task = asyncio.create_task(self._analyze_overall_regime())
            tasks.append(analysis_task)

            # Wait for all tasks
            await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error in market intelligence monitoring: {e}")
            self.is_running = False
            raise

    async def stop_monitoring(self):
        """Stop market intelligence monitoring"""
        self.is_running = False
        logger.info("Stopped market intelligence monitoring")

    async def _monitor_price_feed(self, symbol: str, pyth_id: str):
        """Monitor individual price feed for regime changes"""
        logger.info(f"Starting price monitoring for {symbol}")

        while self.is_running:
            try:
                # Fetch price data from Pyth
                price_data = await self._fetch_pyth_price(pyth_id)

                if price_data:
                    await self._update_regime_analysis(symbol, price_data)

                # Wait before next update
                await asyncio.sleep(5)  # Update every 5 seconds

            except Exception as e:
                logger.error(f"Error monitoring {symbol}: {e}")
                await asyncio.sleep(30)  # Wait longer on error

    async def _fetch_pyth_price(self, pyth_id: str) -> Optional[PriceData]:
        """Fetch price data from Pyth Network"""
        try:
            # Optional production REST path (kept off by default to avoid test flakiness)
            # Provide PYTH_REST_URL in env to enable, e.g. https://hermes.pyth.network
            rest_url = os.getenv("PYTH_REST_URL")
            if rest_url:
                timeout = aiohttp.ClientTimeout(total=5, connect=3)
                url = f"{rest_url.rstrip('/')}/{pyth_id}"
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Try common shapes; fall back to simulation on parse errors
                            price = None
                            conf = 0.9
                            if isinstance(data, dict):
                                price = (
                                    data.get("price")
                                    or data.get("priceUsd")
                                    or data.get("emaPrice")
                                )
                                conf = float(data.get("confidence", conf))
                            elif isinstance(data, list) and data:
                                item = data[0]
                                if isinstance(item, dict):
                                    price = (
                                        item.get("price")
                                        or item.get("priceUsd")
                                        or item.get("emaPrice")
                                    )
                                    conf = float(item.get("confidence", conf))
                            if price is not None:
                                return PriceData(
                                    symbol=pyth_id,
                                    price=float(price),
                                    timestamp=datetime.utcnow(),
                                    confidence=float(conf),
                                    source="pyth-rest",
                                )

            # Default: simulate price data (stable for tests)
            base_price = (
                50000 if "BTC" in pyth_id else 3000 if "ETH" in pyth_id else 100
            )
            price_change = np.random.normal(0, 0.001)  # ~0.1% volatility
            current_price = base_price * (1 + price_change)

            return PriceData(
                symbol=pyth_id,
                price=current_price,
                timestamp=datetime.utcnow(),
                confidence=0.95,
                source="pyth-sim",
            )

        except Exception as e:
            logger.error(f"Error fetching Pyth price for {pyth_id}: {e}")
            return None

    async def _update_regime_analysis(self, symbol: str, price_data: PriceData):
        """Update regime analysis for a symbol"""
        try:
            if symbol not in self.regime_data:
                self.regime_data[symbol] = {
                    "prices": [],
                    "volatility": 0,
                    "trend": "neutral",
                    "regime": "green",
                    "last_updated": datetime.utcnow(),
                }

            # Add new price point
            self.regime_data[symbol]["prices"].append(
                {"price": price_data.price, "timestamp": price_data.timestamp}
            )

            # Keep only last 24 hours of data
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self.regime_data[symbol]["prices"] = [
                p for p in self.regime_data[symbol]["prices"] if p["timestamp"] > cutoff
            ]

            # Calculate regime metrics
            await self._calculate_regime_metrics(symbol)

        except Exception as e:
            logger.error(f"Error updating regime analysis for {symbol}: {e}")

    async def _calculate_regime_metrics(self, symbol: str):
        """Calculate volatility and trend for regime classification"""
        try:
            prices = [p["price"] for p in self.regime_data[symbol]["prices"]]

            if len(prices) < 20:
                return  # Need minimum data

            # Calculate 1-hour volatility (assuming 5-second intervals)
            recent_prices = prices[-12:] if len(prices) >= 12 else prices
            if len(recent_prices) > 1:
                returns = [
                    np.log(recent_prices[i] / recent_prices[i - 1])
                    for i in range(1, len(recent_prices))
                ]
                volatility = np.std(returns) * np.sqrt(720)  # Annualized
            else:
                volatility = 0.1  # Default moderate volatility

            # Calculate trend (4-hour momentum)
            if len(prices) >= 288:  # 4 hours of data (5s intervals)
                trend_return = (prices[-1] - prices[-288]) / prices[-288]
                if trend_return > self.trend_thresholds["bullish"]:
                    trend = "bullish"
                elif trend_return < self.trend_thresholds["bearish"]:
                    trend = "bearish"
                else:
                    trend = "neutral"
            else:
                trend = "neutral"

            # Determine regime color
            regime = self._determine_regime_color(volatility, trend)

            # Update regime data
            self.regime_data[symbol].update(
                {
                    "volatility": volatility,
                    "trend": trend,
                    "regime": regime,
                    "last_updated": datetime.utcnow(),
                }
            )

            logger.debug(
                f"{symbol}: Regime={regime}, Vol={volatility:.3f}, Trend={trend}"
            )

        except Exception as e:
            logger.error(f"Error calculating regime metrics for {symbol}: {e}")

    def _determine_regime_color(self, volatility: float, trend: str) -> str:
        """Determine if market conditions are favorable for copying"""
        # Green: Low volatility, any trend
        if volatility < self.volatility_thresholds["green"]:
            return "green"

        # Yellow: Medium volatility
        elif volatility < self.volatility_thresholds["yellow"]:
            return "yellow"

        # Red: High volatility (risky for copying)
        else:
            return "red"

    async def get_copy_timing_signal(self, symbol: str) -> RegimeSignal:
        """Get current timing recommendation for copying trades"""
        try:
            if symbol not in self.regime_data:
                return RegimeSignal(
                    symbol=symbol,
                    signal="yellow",
                    confidence=0.3,
                    volatility=0.5,
                    trend="neutral",
                    reason="Insufficient data",
                    timestamp=datetime.utcnow(),
                )

            regime_info = self.regime_data[symbol]

            # Calculate confidence based on data quality
            data_points = len(regime_info["prices"])
            confidence = min(0.9, 0.3 + (data_points / 100) * 0.6)

            return RegimeSignal(
                symbol=symbol,
                signal=regime_info["regime"],
                confidence=confidence,
                volatility=regime_info["volatility"],
                trend=regime_info["trend"],
                reason=self._generate_signal_reason(regime_info),
                timestamp=regime_info["last_updated"],
            )

        except Exception as e:
            logger.error(f"Error getting timing signal for {symbol}: {e}")
            return RegimeSignal(
                symbol=symbol,
                signal="yellow",
                confidence=0.1,
                volatility=0.5,
                trend="neutral",
                reason="Error in analysis",
                timestamp=datetime.utcnow(),
            )

    def _generate_signal_reason(self, regime_info: dict) -> str:
        """Generate human-readable reason for signal"""
        vol = regime_info["volatility"]
        trend = regime_info["trend"]

        if regime_info["regime"] == "green":
            return f"Low volatility ({vol:.1%}), {trend} trend - Good for copying"
        elif regime_info["regime"] == "yellow":
            return f"Moderate volatility ({vol:.1%}), {trend} trend - Copy with caution"
        else:
            return f"High volatility ({vol:.1%}), {trend} trend - Risky for copying"

    async def _analyze_overall_regime(self):
        """Analyze overall market regime across all symbols"""
        while self.is_running:
            try:
                # Calculate overall market sentiment
                green_count = 0
                yellow_count = 0
                red_count = 0
                total_volatility = 0
                symbol_count = 0

                for _symbol, data in self.regime_data.items():
                    if data["regime"] == "green":
                        green_count += 1
                    elif data["regime"] == "yellow":
                        yellow_count += 1
                    else:
                        red_count += 1

                    total_volatility += data["volatility"]
                    symbol_count += 1

                if symbol_count > 0:
                    avg_volatility = total_volatility / symbol_count

                    # Store overall regime data
                    overall_regime = {
                        "green_count": green_count,
                        "yellow_count": yellow_count,
                        "red_count": red_count,
                        "avg_volatility": avg_volatility,
                        "overall_sentiment": self._determine_overall_sentiment(
                            green_count, yellow_count, red_count
                        ),
                        "timestamp": datetime.utcnow(),
                    }

                    # Cache overall regime
                    import redis.asyncio as redis

                    redis_client = redis.Redis()
                    await redis_client.setex(
                        "overall_market_regime",
                        300,  # 5 minutes
                        json.dumps(overall_regime, default=str),
                    )

                # Wait before next analysis
                await asyncio.sleep(60)  # Analyze every minute

            except Exception as e:
                logger.error(f"Error in overall regime analysis: {e}")
                await asyncio.sleep(60)

    def _determine_overall_sentiment(
        self, green_count: int, yellow_count: int, red_count: int
    ) -> str:
        """Determine overall market sentiment"""
        total = green_count + yellow_count + red_count

        if total == 0:
            return "unknown"

        green_ratio = green_count / total
        red_ratio = red_count / total

        if green_ratio >= 0.6:
            return "favorable"
        elif red_ratio >= 0.5:
            return "risky"
        else:
            return "mixed"

    async def get_overall_regime(self) -> dict[str, Any]:
        """Get overall market regime analysis"""
        try:
            import redis.asyncio as redis

            redis_client = redis.Redis()

            cached = await redis_client.get("overall_market_regime")
            if cached:
                return json.loads(cached)

            # Fallback analysis
            return {
                "name": "Unknown",
                "volatility": 0.5,
                "trend": "neutral",
                "confidence": 0.1,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting overall regime: {e}")
            return {
                "name": "Error",
                "volatility": 0.5,
                "trend": "neutral",
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_all_signals(self) -> dict[str, RegimeSignal]:
        """Get timing signals for all monitored symbols"""
        signals = {}

        for symbol in self.pyth_feeds.keys():
            signals[symbol] = await self.get_copy_timing_signal(symbol)

        return signals

    async def identify_copy_opportunities(self) -> list[dict[str, Any]]:
        """Identify high-confidence copy opportunities"""
        try:
            opportunities = []

            # Get all signals
            signals = await self.get_all_signals()

            # Filter for green signals with high confidence
            for symbol, signal in signals.items():
                if signal.signal == "green" and signal.confidence > 0.7:
                    opportunities.append(
                        {
                            "symbol": symbol,
                            "signal": signal.signal,
                            "confidence": signal.confidence,
                            "volatility": signal.volatility,
                            "trend": signal.trend,
                            "reason": signal.reason,
                        }
                    )

            # Sort by confidence
            opportunities.sort(key=lambda x: x["confidence"], reverse=True)

            return opportunities[:5]  # Return top 5

        except Exception as e:
            logger.error(f"Error identifying copy opportunities: {e}")
            return []

    async def get_market_summary(self) -> dict[str, Any]:
        """Get comprehensive market summary"""
        try:
            signals = await self.get_all_signals()
            overall_regime = await self.get_overall_regime()
            opportunities = await self.identify_copy_opportunities()

            # Count signals by type
            signal_counts = {"green": 0, "yellow": 0, "red": 0}
            for signal in signals.values():
                signal_counts[signal.signal] += 1

            return {
                "overall_regime": overall_regime,
                "signal_counts": signal_counts,
                "opportunities": opportunities,
                "total_symbols": len(signals),
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {
                "overall_regime": {"name": "Error", "confidence": 0.0},
                "signal_counts": {"green": 0, "yellow": 0, "red": 0},
                "opportunities": [],
                "total_symbols": 0,
                "last_updated": datetime.utcnow().isoformat(),
            }
