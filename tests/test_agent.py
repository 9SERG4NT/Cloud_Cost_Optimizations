import asyncio
import httpx
from backend.agent import _call_llm_openai

async def main():
    async with httpx.AsyncClient() as client:
        try:
            res = await _call_llm_openai(client, [{'role':'user','content':'hi'}], [])
            print(res)
        except Exception as e:
            print("Exception:", e)

asyncio.run(main())
