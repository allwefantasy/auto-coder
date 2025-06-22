import asyncio
from autocoder.sdk import modify_code_stream, AutoCodeOptions        
async def main():
    options = AutoCodeOptions(model="v3_chat")
    async for event in modify_code_stream(
        "Refactor the user authentication module",
        options=options
    ):
        print(f"[{event.event_type}] {event.data}")

asyncio.run(main())