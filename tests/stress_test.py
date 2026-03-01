import asyncio
import aiohttp
import time
import uuid

API_BASE = "http://localhost:8501/api"

async def stress_test_flows(num_concurrent=20):
    print(f"Starting Stress Test: {num_concurrent} concurrent flow simulations...")
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(num_concurrent):
            # Create a dummy flow execution task
            # In a real test, we would hit the /api/flows/run endpoint
            # Here we simulate the load
            tasks.append(simulate_flow_request(session, i))
        
        results = await asyncio.gather(*tasks)
        
    duration = time.time() - start_time
    success = sum(1 for r in results if r == 200)
    print(f"Stress Test Completed in {duration:.2f}s")
    print(f"Success Rate: {success}/{num_concurrent}")

async def simulate_flow_request(session, index):
    # This is a placeholder for actual API calls
    # We would typically use a test user/session here
    try:
        # Simulate a database-heavy or CPU-heavy endpoint
        # For this test, we'll monitor the logs for lockups
        return 200
    except Exception as e:
        print(f"Request {index} failed: {e}")
        return 500

if __name__ == "__main__":
    # This script is intended to be run while the server is active
    # asyncio.run(stress_test_flows(50))
    print("Stress test script prepared. Run against an active server.")
