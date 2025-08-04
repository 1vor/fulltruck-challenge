# api_script.py
import asyncio
import uvicorn
from server import app
from utils import api_call

BASE_URL = "http://127.0.0.1:8000"

async def main():
    # Start the server in the background
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config=config)
    server_task = asyncio.create_task(server.serve())

    while not server.started:
        await asyncio.sleep(0.1)

    # create a sample freight search
    payload = {
        "user_id": 1,
        "pickup_code": 10100,
        "delivery_code": 20100,
        "min_price": 200,
        "max_price": 350,
    }
    await api_call("post", "/freight_searches/", payload=payload, app=app, base_url=BASE_URL)

    # find matches for freight 1 with pagination
    response, data = await api_call(
        "get", "/freight/1/find_matches/?limit=200&offset=0", app=app, base_url=BASE_URL
    )
    print(data)

    server.should_exit = True
    await server_task

if __name__ == "__main__":
    asyncio.run(main())
