import asyncio
from crawl4ai import *

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://uelng8wukz.feishu.cn/wiki/K3MTwbmaXiO8ixkFpHAc8l7onpe?fromScene=spaceOverview",
        )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())