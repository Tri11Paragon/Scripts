from pool import PlaywrightPool
import asyncio
import trafilatura

article = "https://financialpost.com/news/economy/ontario-and-quebec-economies-to-be-hardest-hit-this-year-by-trade-war-deloitte"

async def main() -> None:
    await PlaywrightPool.start()

    html = await PlaywrightPool.fetch_html(article)

    print(trafilatura.extract(html))

    await PlaywrightPool.stop()

asyncio.run(main())