#!/usr/bin/env python3
"""Load testing script for nonce reservation under high concurrency."""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.blockchain.tx.nonce_manager import NonceManager
from src.blockchain.tx.nonce_store import InMemoryNonceStore, RedisNonceStore, HybridNonceStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class NonceLoadTester:
    """Load tester for nonce reservation system."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.results: List[Dict[str, Any]] = []
        
    async def test_in_memory_store(self, num_requests: int = 1000, concurrency: int = 50):
        """Test in-memory nonce store under load."""
        logger.info(f"Testing in-memory store: {num_requests} requests, {concurrency} concurrent")
        
        store = InMemoryNonceStore()
        manager = NonceManager(store)
        
        start_time = time.time()
        
        async def reserve_nonce(request_id: int):
            try:
                async with manager.reserve() as nonce:
                    return {
                        'request_id': request_id,
                        'nonce': nonce,
                        'success': True,
                        'error': None
                    }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'nonce': None,
                    'success': False,
                    'error': str(e)
                }
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency)
        
        async def limited_reserve(request_id: int):
            async with semaphore:
                return await reserve_nonce(request_id)
        
        # Run concurrent requests
        tasks = [limited_reserve(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Analyze results
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        nonces = [r['nonce'] for r in successful]
        nonce_collisions = len(nonces) - len(set(nonces))
        
        logger.info(f"In-memory results:")
        logger.info(f"  Total requests: {num_requests}")
        logger.info(f"  Successful: {len(successful)}")
        logger.info(f"  Failed: {len(failed)}")
        logger.info(f"  Nonce collisions: {nonce_collisions}")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  Requests/sec: {num_requests/duration:.2f}")
        
        if failed:
            logger.warning(f"  Errors: {[f['error'] for f in failed[:5]]}")
        
        return {
            'store_type': 'in_memory',
            'total_requests': num_requests,
            'successful': len(successful),
            'failed': len(failed),
            'nonce_collisions': nonce_collisions,
            'duration': duration,
            'requests_per_sec': num_requests/duration,
            'success_rate': len(successful)/num_requests
        }
    
    async def test_redis_store(self, num_requests: int = 1000, concurrency: int = 50):
        """Test Redis nonce store under load."""
        logger.info(f"Testing Redis store: {num_requests} requests, {concurrency} concurrent")
        
        try:
            store = RedisNonceStore(self.redis_url)
            manager = NonceManager(store)
            
            start_time = time.time()
            
            async def reserve_nonce(request_id: int):
                try:
                    async with manager.reserve() as nonce:
                        return {
                            'request_id': request_id,
                            'nonce': nonce,
                            'success': True,
                            'error': None
                        }
                except Exception as e:
                    return {
                        'request_id': request_id,
                        'nonce': None,
                        'success': False,
                        'error': str(e)
                    }
            
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(concurrency)
            
            async def limited_reserve(request_id: int):
                async with semaphore:
                    return await reserve_nonce(request_id)
            
            # Run concurrent requests
            tasks = [limited_reserve(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Analyze results
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            nonces = [r['nonce'] for r in successful]
            nonce_collisions = len(nonces) - len(set(nonces))
            
            logger.info(f"Redis results:")
            logger.info(f"  Total requests: {num_requests}")
            logger.info(f"  Successful: {len(successful)}")
            logger.info(f"  Failed: {len(failed)}")
            logger.info(f"  Nonce collisions: {nonce_collisions}")
            logger.info(f"  Duration: {duration:.2f}s")
            logger.info(f"  Requests/sec: {num_requests/duration:.2f}")
            
            if failed:
                logger.warning(f"  Errors: {[f['error'] for f in failed[:5]]}")
            
            return {
                'store_type': 'redis',
                'total_requests': num_requests,
                'successful': len(successful),
                'failed': len(failed),
                'nonce_collisions': nonce_collisions,
                'duration': duration,
                'requests_per_sec': num_requests/duration,
                'success_rate': len(successful)/num_requests
            }
            
        except Exception as e:
            logger.error(f"Redis store test failed: {e}")
            return {
                'store_type': 'redis',
                'error': str(e),
                'success_rate': 0
            }
    
    async def test_hybrid_store(self, num_requests: int = 1000, concurrency: int = 50):
        """Test hybrid nonce store under load."""
        logger.info(f"Testing hybrid store: {num_requests} requests, {concurrency} concurrent")
        
        try:
            store = HybridNonceStore(self.redis_url)
            manager = NonceManager(store)
            
            start_time = time.time()
            
            async def reserve_nonce(request_id: int):
                try:
                    async with manager.reserve() as nonce:
                        return {
                            'request_id': request_id,
                            'nonce': nonce,
                            'success': True,
                            'error': None
                        }
                except Exception as e:
                    return {
                        'request_id': request_id,
                        'nonce': None,
                        'success': False,
                        'error': str(e)
                    }
            
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(concurrency)
            
            async def limited_reserve(request_id: int):
                async with semaphore:
                    return await reserve_nonce(request_id)
            
            # Run concurrent requests
            tasks = [limited_reserve(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Analyze results
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]
            
            nonces = [r['nonce'] for r in successful]
            nonce_collisions = len(nonces) - len(set(nonces))
            
            logger.info(f"Hybrid results:")
            logger.info(f"  Total requests: {num_requests}")
            logger.info(f"  Successful: {len(successful)}")
            logger.info(f"  Failed: {len(failed)}")
            logger.info(f"  Nonce collisions: {nonce_collisions}")
            logger.info(f"  Duration: {duration:.2f}s")
            logger.info(f"  Requests/sec: {num_requests/duration:.2f}")
            
            if failed:
                logger.warning(f"  Errors: {[f['error'] for f in failed[:5]]}")
            
            return {
                'store_type': 'hybrid',
                'total_requests': num_requests,
                'successful': len(successful),
                'failed': len(failed),
                'nonce_collisions': nonce_collisions,
                'duration': duration,
                'requests_per_sec': num_requests/duration,
                'success_rate': len(successful)/num_requests
            }
            
        except Exception as e:
            logger.error(f"Hybrid store test failed: {e}")
            return {
                'store_type': 'hybrid',
                'error': str(e),
                'success_rate': 0
            }
    
    async def run_comprehensive_test(self):
        """Run comprehensive load test across all store types."""
        logger.info("🚀 Starting comprehensive nonce load testing")
        
        test_configs = [
            {'requests': 100, 'concurrency': 10},
            {'requests': 500, 'concurrency': 25},
            {'requests': 1000, 'concurrency': 50},
        ]
        
        all_results = []
        
        for config in test_configs:
            logger.info(f"\n📊 Testing configuration: {config['requests']} requests, {config['concurrency']} concurrent")
            
            # Test in-memory store
            in_memory_result = await self.test_in_memory_store(
                config['requests'], config['concurrency']
            )
            all_results.append(in_memory_result)
            
            # Test Redis store
            redis_result = await self.test_redis_store(
                config['requests'], config['concurrency']
            )
            all_results.append(redis_result)
            
            # Test hybrid store
            hybrid_result = await self.test_hybrid_store(
                config['requests'], config['concurrency']
            )
            all_results.append(hybrid_result)
        
        # Generate summary report
        self.generate_summary_report(all_results)
        
        return all_results
    
    def generate_summary_report(self, results: List[Dict[str, Any]]):
        """Generate summary report of load test results."""
        logger.info("\n📈 LOAD TEST SUMMARY REPORT")
        logger.info("=" * 50)
        
        # Group results by store type
        by_store = {}
        for result in results:
            store_type = result['store_type']
            if store_type not in by_store:
                by_store[store_type] = []
            by_store[store_type].append(result)
        
        for store_type, store_results in by_store.items():
            logger.info(f"\n🏪 {store_type.upper()} STORE:")
            
            success_rates = [r.get('success_rate', 0) for r in store_results if 'success_rate' in r]
            rps_values = [r.get('requests_per_sec', 0) for r in store_results if 'requests_per_sec' in r]
            collision_counts = [r.get('nonce_collisions', 0) for r in store_results if 'nonce_collisions' in r]
            
            if success_rates:
                logger.info(f"  Success Rate: {statistics.mean(success_rates):.2%} (avg)")
                logger.info(f"  Requests/sec: {statistics.mean(rps_values):.2f} (avg)")
                logger.info(f"  Nonce Collisions: {sum(collision_counts)} (total)")
                
                # Check for issues
                if statistics.mean(success_rates) < 0.99:
                    logger.warning(f"  ⚠️  Low success rate detected!")
                if sum(collision_counts) > 0:
                    logger.warning(f"  ⚠️  Nonce collisions detected!")
                if statistics.mean(rps_values) < 100:
                    logger.warning(f"  ⚠️  Low throughput detected!")
        
        logger.info("\n✅ Load testing completed!")


async def main():
    """Main function to run load tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Nonce reservation load testing')
    parser.add_argument('--redis-url', default='redis://localhost:6379', help='Redis URL')
    parser.add_argument('--requests', type=int, default=1000, help='Number of requests')
    parser.add_argument('--concurrency', type=int, default=50, help='Concurrency level')
    parser.add_argument('--store-type', choices=['in_memory', 'redis', 'hybrid', 'all'], 
                       default='all', help='Store type to test')
    
    args = parser.parse_args()
    
    tester = NonceLoadTester(args.redis_url)
    
    if args.store_type == 'all':
        await tester.run_comprehensive_test()
    elif args.store_type == 'in_memory':
        await tester.test_in_memory_store(args.requests, args.concurrency)
    elif args.store_type == 'redis':
        await tester.test_redis_store(args.requests, args.concurrency)
    elif args.store_type == 'hybrid':
        await tester.test_hybrid_store(args.requests, args.concurrency)


if __name__ == '__main__':
    asyncio.run(main())
