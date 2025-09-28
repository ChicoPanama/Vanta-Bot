#!/usr/bin/env python3
"""Health endpoint validation script for production readiness."""

import asyncio
import aiohttp
import time
import json
import sys
from typing import Dict, Any, List
import statistics

class HealthEndpointValidator:
    """Validator for health endpoints."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.endpoints = [
            '/healthz',
            '/readyz', 
            '/health',
            '/metrics',
            '/oracle/status'
        ]
        self.results: List[Dict[str, Any]] = []
    
    async def test_endpoint(self, endpoint: str, timeout: float = 0.5) -> Dict[str, Any]:
        """Test a single health endpoint."""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    # Read response content
                    content = await response.text()
                    
                    # Try to parse JSON
                    try:
                        json_data = json.loads(content)
                    except json.JSONDecodeError:
                        json_data = None
                    
                    return {
                        'endpoint': endpoint,
                        'status_code': response.status,
                        'response_time': response_time,
                        'success': response.status == 200,
                        'content_length': len(content),
                        'has_json': json_data is not None,
                        'json_keys': list(json_data.keys()) if json_data else [],
                        'error': None
                    }
                    
        except asyncio.TimeoutError:
            end_time = time.time()
            return {
                'endpoint': endpoint,
                'status_code': None,
                'response_time': end_time - start_time,
                'success': False,
                'content_length': 0,
                'has_json': False,
                'json_keys': [],
                'error': 'timeout'
            }
        except Exception as e:
            end_time = time.time()
            return {
                'endpoint': endpoint,
                'status_code': None,
                'response_time': end_time - start_time,
                'success': False,
                'content_length': 0,
                'has_json': False,
                'json_keys': [],
                'error': str(e)
            }
    
    async def test_all_endpoints(self, iterations: int = 10) -> List[Dict[str, Any]]:
        """Test all endpoints multiple times."""
        print(f"🔍 Testing {len(self.endpoints)} endpoints with {iterations} iterations each")
        
        all_results = []
        
        for iteration in range(iterations):
            print(f"  Iteration {iteration + 1}/{iterations}")
            
            # Test all endpoints concurrently
            tasks = [self.test_endpoint(endpoint) for endpoint in self.endpoints]
            results = await asyncio.gather(*tasks)
            
            all_results.extend(results)
            
            # Small delay between iterations
            await asyncio.sleep(0.1)
        
        return all_results
    
    def analyze_results(self, results: List[Dict[str, Any]]):
        """Analyze test results and generate report."""
        print("\n📊 HEALTH ENDPOINT VALIDATION REPORT")
        print("=" * 50)
        
        # Group results by endpoint
        by_endpoint = {}
        for result in results:
            endpoint = result['endpoint']
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = []
            by_endpoint[endpoint].append(result)
        
        overall_success = 0
        total_tests = 0
        
        for endpoint, endpoint_results in by_endpoint.items():
            print(f"\n🔗 {endpoint}:")
            
            success_count = sum(1 for r in endpoint_results if r['success'])
            total_count = len(endpoint_results)
            success_rate = success_count / total_count if total_count > 0 else 0
            
            response_times = [r['response_time'] for r in endpoint_results if r['success']]
            avg_response_time = statistics.mean(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            print(f"  Success Rate: {success_rate:.2%} ({success_count}/{total_count})")
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            print(f"  Max Response Time: {max_response_time:.3f}s")
            
            # Check for issues
            if success_rate < 1.0:
                print(f"  ⚠️  FAILURES DETECTED:")
                failures = [r for r in endpoint_results if not r['success']]
                for failure in failures[:3]:  # Show first 3 failures
                    print(f"    - {failure['error'] or f'Status {failure['status_code']}'}")
            
            if max_response_time > 0.5:
                print(f"  ⚠️  SLOW RESPONSES: Max {max_response_time:.3f}s > 0.5s threshold")
            
            # Check JSON structure for specific endpoints
            if endpoint in ['/health', '/oracle/status']:
                json_results = [r for r in endpoint_results if r['has_json']]
                if json_results:
                    sample_keys = json_results[0]['json_keys']
                    print(f"  JSON Keys: {sample_keys}")
                    
                    # Validate expected keys
                    if endpoint == '/health':
                        expected_keys = ['status', 'checks', 'oracle_status']
                        missing_keys = [k for k in expected_keys if k not in sample_keys]
                        if missing_keys:
                            print(f"  ⚠️  Missing expected keys: {missing_keys}")
                    
                    if endpoint == '/oracle/status':
                        expected_keys = ['execution_mode', 'oracle_providers']
                        missing_keys = [k for k in expected_keys if k not in sample_keys]
                        if missing_keys:
                            print(f"  ⚠️  Missing expected keys: {missing_keys}")
            
            overall_success += success_count
            total_tests += total_count
        
        # Overall summary
        overall_success_rate = overall_success / total_tests if total_tests > 0 else 0
        print(f"\n🎯 OVERALL SUMMARY:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful: {overall_success}")
        print(f"  Success Rate: {overall_success_rate:.2%}")
        
        if overall_success_rate >= 0.99:
            print("  ✅ HEALTH ENDPOINTS: PRODUCTION READY")
        elif overall_success_rate >= 0.95:
            print("  ⚠️  HEALTH ENDPOINTS: MOSTLY READY (minor issues)")
        else:
            print("  ❌ HEALTH ENDPOINTS: NOT READY (significant issues)")
        
        return overall_success_rate >= 0.99
    
    async def test_under_load(self, concurrent_requests: int = 50, duration_seconds: int = 10):
        """Test endpoints under load."""
        print(f"\n🚀 LOAD TESTING: {concurrent_requests} concurrent requests for {duration_seconds}s")
        
        start_time = time.time()
        request_count = 0
        success_count = 0
        response_times = []
        
        async def make_request():
            nonlocal request_count, success_count
            while time.time() - start_time < duration_seconds:
                # Pick random endpoint
                import random
                endpoint = random.choice(self.endpoints)
                
                result = await self.test_endpoint(endpoint, timeout=1.0)
                request_count += 1
                if result['success']:
                    success_count += 1
                    response_times.append(result['response_time'])
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.01)
        
        # Start concurrent requests
        tasks = [make_request() for _ in range(concurrent_requests)]
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        print(f"\n📈 LOAD TEST RESULTS:")
        print(f"  Duration: {actual_duration:.2f}s")
        print(f"  Total Requests: {request_count}")
        print(f"  Successful: {success_count}")
        print(f"  Success Rate: {success_count/request_count:.2%}")
        print(f"  Requests/sec: {request_count/actual_duration:.2f}")
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            print(f"  Avg Response Time: {avg_response_time:.3f}s")
            print(f"  Max Response Time: {max_response_time:.3f}s")
            
            if max_response_time > 0.5:
                print("  ⚠️  SLOW RESPONSES UNDER LOAD")
        
        return success_count/request_count >= 0.99


async def main():
    """Main function to run health validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Health endpoint validation')
    parser.add_argument('--base-url', default='http://localhost:8080', help='Base URL for health endpoints')
    parser.add_argument('--iterations', type=int, default=10, help='Number of test iterations')
    parser.add_argument('--load-test', action='store_true', help='Run load test')
    parser.add_argument('--concurrent', type=int, default=50, help='Concurrent requests for load test')
    parser.add_argument('--duration', type=int, default=10, help='Load test duration in seconds')
    
    args = parser.parse_args()
    
    validator = HealthEndpointValidator(args.base_url)
    
    # Basic endpoint testing
    results = await validator.test_all_endpoints(args.iterations)
    is_ready = validator.analyze_results(results)
    
    # Load testing if requested
    if args.load_test:
        load_ready = await validator.test_under_load(args.concurrent, args.duration)
        is_ready = is_ready and load_ready
    
    # Exit with appropriate code
    sys.exit(0 if is_ready else 1)


if __name__ == '__main__':
    asyncio.run(main())
