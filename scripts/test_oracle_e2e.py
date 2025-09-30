#!/usr/bin/env python3
"""End-to-end oracle testing script for production validation."""

import asyncio
import os
import sys
import time
from typing import Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from web3 import Web3

from src.services.markets.symbols import is_supported_symbol, to_canonical
from src.services.oracle import OracleFacade, create_price_validator
from src.services.oracle_providers.chainlink import ChainlinkOracle
from src.services.oracle_providers.pyth import PythOracle
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OracleE2ETester:
    """End-to-end oracle testing."""

    def __init__(self, base_rpc_url: str = "https://mainnet.base.org"):
        self.base_rpc_url = base_rpc_url
        self.test_symbols = ["BTC/USD", "ETH/USD", "SOL/USD"]
        self.results: list[dict[str, Any]] = []

    async def test_symbol_normalization(self):
        """Test symbol normalization end-to-end."""
        logger.info("🔍 Testing symbol normalization")

        test_cases = [
            ("BTC/USD", "BTC"),
            ("ETH/USD", "ETH"),
            ("SOL/USD", "SOL"),
            ("BTC", "BTC"),
            ("ETH", "ETH"),
            ("SOL", "SOL"),
        ]

        for input_symbol, expected_canonical in test_cases:
            canonical = to_canonical(input_symbol)
            is_supported = is_supported_symbol(input_symbol)

            result = {
                "input": input_symbol,
                "canonical": canonical,
                "expected_canonical": expected_canonical,
                "is_supported": is_supported,
                "success": canonical == expected_canonical and is_supported,
            }

            self.results.append(result)

            if result["success"]:
                logger.info(
                    f"  ✅ {input_symbol} -> {canonical} (supported: {is_supported})"
                )
            else:
                logger.error(
                    f"  ❌ {input_symbol} -> {canonical} (expected: {expected_canonical}, supported: {is_supported})"
                )

        return all(r["success"] for r in self.results)

    async def test_pyth_oracle(self):
        """Test Pyth oracle end-to-end."""
        logger.info("🔍 Testing Pyth oracle")

        pyth = PythOracle()

        for symbol in self.test_symbols:
            try:
                start_time = time.time()
                result = await pyth.get_price(symbol)
                end_time = time.time()

                response_time = end_time - start_time

                result_data = {
                    "provider": "pyth",
                    "symbol": symbol,
                    "price": result.price,
                    "timestamp": result.timestamp,
                    "deviation_bps": result.deviation_bps,
                    "freshness_sec": result.freshness_sec,
                    "response_time": response_time,
                    "success": True,
                    "error": None,
                }

                self.results.append(result_data)

                logger.info(
                    f"  ✅ Pyth {symbol}: ${result.price} (dev: {result.deviation_bps}bps, age: {result.freshness_sec}s, {response_time:.3f}s)"
                )

                # Validate price is reasonable
                if result.price < 0:
                    logger.warning(f"  ⚠️  Negative price for {symbol}: {result.price}")

                # Validate freshness
                if result.freshness_sec > 60:
                    logger.warning(
                        f"  ⚠️  Stale price for {symbol}: {result.freshness_sec}s"
                    )

            except Exception as e:
                result_data = {
                    "provider": "pyth",
                    "symbol": symbol,
                    "price": None,
                    "timestamp": None,
                    "deviation_bps": None,
                    "freshness_sec": None,
                    "response_time": None,
                    "success": False,
                    "error": str(e),
                }

                self.results.append(result_data)
                logger.error(f"  ❌ Pyth {symbol}: {e}")

    async def test_chainlink_oracle(self):
        """Test Chainlink oracle end-to-end."""
        logger.info("🔍 Testing Chainlink oracle")

        try:
            w3 = Web3(
                Web3.HTTPProvider(self.base_rpc_url, request_kwargs={"timeout": 15})
            )
            chainlink = ChainlinkOracle(
                w3, validate_on_init=False
            )  # Skip startup validation for testing

            for symbol in self.test_symbols:
                try:
                    start_time = time.time()
                    result = await chainlink.get_price(symbol)
                    end_time = time.time()

                    response_time = end_time - start_time

                    result_data = {
                        "provider": "chainlink",
                        "symbol": symbol,
                        "price": result.price,
                        "timestamp": result.timestamp,
                        "deviation_bps": result.deviation_bps,
                        "freshness_sec": result.freshness_sec,
                        "response_time": response_time,
                        "success": True,
                        "error": None,
                    }

                    self.results.append(result_data)

                    logger.info(
                        f"  ✅ Chainlink {symbol}: ${result.price} (dev: {result.deviation_bps}bps, age: {result.freshness_sec}s, {response_time:.3f}s)"
                    )

                    # Validate price is reasonable
                    if result.price < 0:
                        logger.warning(
                            f"  ⚠️  Negative price for {symbol}: {result.price}"
                        )

                    # Validate freshness
                    if result.freshness_sec > 3600:  # 1 hour
                        logger.warning(
                            f"  ⚠️  Stale price for {symbol}: {result.freshness_sec}s"
                        )

                except Exception as e:
                    result_data = {
                        "provider": "chainlink",
                        "symbol": symbol,
                        "price": None,
                        "timestamp": None,
                        "deviation_bps": None,
                        "freshness_sec": None,
                        "response_time": None,
                        "success": False,
                        "error": str(e),
                    }

                    self.results.append(result_data)
                    logger.error(f"  ❌ Chainlink {symbol}: {e}")

        except Exception as e:
            logger.error(f"  ❌ Chainlink oracle initialization failed: {e}")

    async def test_oracle_facade(self):
        """Test oracle facade end-to-end."""
        logger.info("🔍 Testing oracle facade")

        try:
            # Create Pyth oracle
            pyth = PythOracle()

            # Create Chainlink oracle
            w3 = Web3(
                Web3.HTTPProvider(self.base_rpc_url, request_kwargs={"timeout": 15})
            )
            chainlink = ChainlinkOracle(w3, validate_on_init=False)

            # Create facade
            facade = OracleFacade(
                primary_oracle=pyth,
                secondary_oracle=chainlink,
                validator=create_price_validator(),
            )

            for symbol in self.test_symbols:
                try:
                    start_time = time.time()
                    result = await facade.get_price(symbol)
                    end_time = time.time()

                    response_time = end_time - start_time

                    result_data = {
                        "provider": "facade",
                        "symbol": symbol,
                        "price": result.price,
                        "timestamp": result.timestamp,
                        "deviation_bps": result.deviation_bps,
                        "freshness_sec": result.freshness_sec,
                        "response_time": response_time,
                        "success": True,
                        "error": None,
                    }

                    self.results.append(result_data)

                    logger.info(
                        f"  ✅ Facade {symbol}: ${result.price} (dev: {result.deviation_bps}bps, age: {result.freshness_sec}s, {response_time:.3f}s)"
                    )

                    # Validate price is reasonable
                    if result.price < 0:
                        logger.warning(
                            f"  ⚠️  Negative price for {symbol}: {result.price}"
                        )

                    # Validate freshness
                    if result.freshness_sec > 60:
                        logger.warning(
                            f"  ⚠️  Stale price for {symbol}: {result.freshness_sec}s"
                        )

                except Exception as e:
                    result_data = {
                        "provider": "facade",
                        "symbol": symbol,
                        "price": None,
                        "timestamp": None,
                        "deviation_bps": None,
                        "freshness_sec": None,
                        "response_time": None,
                        "success": False,
                        "error": str(e),
                    }

                    self.results.append(result_data)
                    logger.error(f"  ❌ Facade {symbol}: {e}")

        except Exception as e:
            logger.error(f"  ❌ Oracle facade initialization failed: {e}")

    async def test_price_deviation(self):
        """Test price deviation between providers."""
        logger.info("🔍 Testing price deviation between providers")

        try:
            # Get prices from both providers
            pyth = PythOracle()
            w3 = Web3(
                Web3.HTTPProvider(self.base_rpc_url, request_kwargs={"timeout": 15})
            )
            chainlink = ChainlinkOracle(w3, validate_on_init=False)

            for symbol in self.test_symbols:
                try:
                    # Get prices from both providers
                    pyth_result = await pyth.get_price(symbol)
                    chainlink_result = await chainlink.get_price(symbol)

                    # Calculate deviation
                    price_diff = abs(pyth_result.price - chainlink_result.price)
                    avg_price = (pyth_result.price + chainlink_result.price) / 2
                    deviation_bps = (
                        (price_diff / avg_price) * 10000 if avg_price > 0 else 0
                    )

                    result_data = {
                        "test": "price_deviation",
                        "symbol": symbol,
                        "pyth_price": pyth_result.price,
                        "chainlink_price": chainlink_result.price,
                        "deviation_bps": deviation_bps,
                        "success": deviation_bps < 100,  # Less than 1% deviation
                        "error": None,
                    }

                    self.results.append(result_data)

                    if result_data["success"]:
                        logger.info(
                            f"  ✅ {symbol}: Pyth ${pyth_result.price}, Chainlink ${chainlink_result.price} (dev: {deviation_bps:.1f}bps)"
                        )
                    else:
                        logger.warning(
                            f"  ⚠️  {symbol}: High deviation {deviation_bps:.1f}bps (Pyth: ${pyth_result.price}, Chainlink: ${chainlink_result.price})"
                        )

                except Exception as e:
                    result_data = {
                        "test": "price_deviation",
                        "symbol": symbol,
                        "pyth_price": None,
                        "chainlink_price": None,
                        "deviation_bps": None,
                        "success": False,
                        "error": str(e),
                    }

                    self.results.append(result_data)
                    logger.error(f"  ❌ {symbol} deviation test failed: {e}")

        except Exception as e:
            logger.error(f"  ❌ Price deviation test initialization failed: {e}")

    def generate_report(self):
        """Generate comprehensive test report."""
        logger.info("\n📊 ORACLE E2E TEST REPORT")
        logger.info("=" * 50)

        # Group results by test type
        by_test = {}
        for result in self.results:
            test_type = result.get("provider", result.get("test", "unknown"))
            if test_type not in by_test:
                by_test[test_type] = []
            by_test[test_type].append(result)

        overall_success = 0
        total_tests = 0

        for test_type, test_results in by_test.items():
            logger.info(f"\n🔍 {test_type.upper()}:")

            success_count = sum(1 for r in test_results if r.get("success", False))
            total_count = len(test_results)
            success_rate = success_count / total_count if total_count > 0 else 0

            logger.info(f"  Tests: {total_count}")
            logger.info(f"  Successful: {success_count}")
            logger.info(f"  Success Rate: {success_rate:.2%}")

            # Show response times for oracle tests
            if "response_time" in test_results[0]:
                response_times = [
                    r["response_time"] for r in test_results if r.get("response_time")
                ]
                if response_times:
                    avg_time = sum(response_times) / len(response_times)
                    max_time = max(response_times)
                    logger.info(f"  Avg Response Time: {avg_time:.3f}s")
                    logger.info(f"  Max Response Time: {max_time:.3f}s")

                    if max_time > 5.0:
                        logger.warning(
                            f"  ⚠️  Slow responses detected (max: {max_time:.3f}s)"
                        )

            # Show price ranges for oracle tests
            if "price" in test_results[0]:
                prices = [r["price"] for r in test_results if r.get("price")]
                if prices:
                    min_price = min(prices)
                    max_price = max(prices)
                    logger.info(f"  Price Range: ${min_price} - ${max_price}")

            overall_success += success_count
            total_tests += total_count

        # Overall summary
        overall_success_rate = overall_success / total_tests if total_tests > 0 else 0
        logger.info("\n🎯 OVERALL SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Successful: {overall_success}")
        logger.info(f"  Success Rate: {overall_success_rate:.2%}")

        if overall_success_rate >= 0.95:
            logger.info("  ✅ ORACLE SYSTEM: PRODUCTION READY")
        elif overall_success_rate >= 0.80:
            logger.info("  ⚠️  ORACLE SYSTEM: MOSTLY READY (minor issues)")
        else:
            logger.info("  ❌ ORACLE SYSTEM: NOT READY (significant issues)")

        return overall_success_rate >= 0.95

    async def run_comprehensive_test(self):
        """Run comprehensive oracle E2E test."""
        logger.info("🚀 Starting comprehensive oracle E2E testing")

        # Test symbol normalization
        await self.test_symbol_normalization()

        # Test individual providers
        await self.test_pyth_oracle()
        await self.test_chainlink_oracle()

        # Test oracle facade
        await self.test_oracle_facade()

        # Test price deviation
        await self.test_price_deviation()

        # Generate report
        is_ready = self.generate_report()

        return is_ready


async def main():
    """Main function to run oracle E2E tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Oracle E2E testing")
    parser.add_argument(
        "--base-rpc-url", default="https://mainnet.base.org", help="Base RPC URL"
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTC/USD", "ETH/USD", "SOL/USD"],
        help="Symbols to test",
    )

    args = parser.parse_args()

    tester = OracleE2ETester(args.base_rpc_url)
    tester.test_symbols = args.symbols

    is_ready = await tester.run_comprehensive_test()

    # Exit with appropriate code
    sys.exit(0 if is_ready else 1)


if __name__ == "__main__":
    asyncio.run(main())
