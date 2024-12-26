from openai import AsyncOpenAI
import asyncio
import time
from rich.console import Console
from rich.table import Table
import numpy as np
import ray
from loguru import logger
import byzerllm
from concurrent.futures import ThreadPoolExecutor


async def benchmark_openai(
    model: str, parallel: int, api_key: str, base_url: str = None, rounds: int = 1, query: str = "Hello, how are you?"
):
    client = AsyncOpenAI(api_key=api_key, base_url=base_url if base_url else None)
    start_time = time.time()

    async def single_request():
        try:
            t1 = time.time()
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": query}],
            )
            t2 = time.time()
            return t2 - t1
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    all_results = []
    for round_num in range(rounds):
        print(f"Running round {round_num + 1}/{rounds}")
        tasks = [single_request() for _ in range(parallel)]
        results = await asyncio.gather(*tasks)
        all_results.extend(results)

    results = all_results

    # Filter out None values from failed requests
    results = [r for r in results if r is not None]

    end_time = time.time()
    total_time = end_time - start_time

    if not results:
        print("All requests failed")
        return

    # Calculate statistics
    avg_time = np.mean(results)
    p50 = np.percentile(results, 50)
    p90 = np.percentile(results, 90)
    p95 = np.percentile(results, 95)
    p99 = np.percentile(results, 99)

    # Create rich table for output
    console = Console()
    table = Table(title=f"OpenAI Client Benchmark Results (Parallel={parallel})")

    table.add_column("Metric", style="cyan")
    table.add_column("Value (seconds)", style="magenta")

    table.add_row("Total Time", f"{total_time:.2f}")
    table.add_row("Average Response Time", f"{avg_time:.2f}")
    table.add_row("Median (P50)", f"{p50:.2f}")
    table.add_row("P90", f"{p90:.2f}")
    table.add_row("P95", f"{p95:.2f}")
    table.add_row("P99", f"{p99:.2f}")
    table.add_row("Requests/Second", f"{parallel/total_time:.2f}")

    console.print(table)


def benchmark_byzerllm(model: str, parallel: int, rounds: int = 1, query: str = "Hello, how are you?"):
    byzerllm.connect_cluster(address="auto")
    llm = byzerllm.ByzerLLM()
    llm.setup_default_model_name(model)

    def single_request(llm):
        try:
            t1 = time.time()
            llm.chat_oai(
                conversations=[{"role": "user", "content": query}]
            )
            t2 = time.time()
            return t2 - t1
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    start_time = time.time()
    all_results = []
    for round_num in range(rounds):
        print(f"Running round {round_num + 1}/{rounds}")
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            # submit tasks to the executor
            futures = [executor.submit(single_request, llm) for _ in range(parallel)]
            # get results from futures
            results = [future.result() for future in futures]
            all_results.extend(results)

        results = all_results

        # Filter out None values from failed requests
        results = [r for r in results if r is not None]

        end_time = time.time()
        total_time = end_time - start_time

    if not results:
        print("All requests failed")
        return

    # Calculate statistics
    avg_time = np.mean(results)
    p50 = np.percentile(results, 50)
    p90 = np.percentile(results, 90)
    p95 = np.percentile(results, 95)
    p99 = np.percentile(results, 99)

    # Create rich table for output
    console = Console()
    table = Table(title=f"ByzerLLM Client Benchmark Results (Parallel={parallel})")

    table.add_column("Metric", style="cyan")
    table.add_column("Value (seconds)", style="magenta")

    table.add_row("Total Time", f"{total_time:.2f}")
    table.add_row("Average Response Time", f"{avg_time:.2f}")
    table.add_row("Median (P50)", f"{p50:.2f}")
    table.add_row("P90", f"{p90:.2f}")
    table.add_row("P95", f"{p95:.2f}")
    table.add_row("P99", f"{p99:.2f}")
    table.add_row("Requests/Second", f"{parallel/total_time:.2f}")

    console.print(table)
