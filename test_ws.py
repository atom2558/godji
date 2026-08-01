import asyncio
import websockets

async def test_connection():
    uri = "ws://127.0.0.1:8000/ws/live"
    try:
        async with websockets.connect(uri) as ws:
            print("Successfully connected to WebSocket server on ws://127.0.0.1:8000/ws/live!")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
