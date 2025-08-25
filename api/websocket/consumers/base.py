from channels.generic.websocket import AsyncWebsocketConsumer
import json
import functools
import asyncio

class BaseConsumer(AsyncWebsocketConsumer):

    async def _send_json(self, data):
        await self.send(text_data=json.dumps(data))

    async def _send_bytes(self, data):
        await self.send(bytes_data=data)
    
    async def _run_blocking(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    
    async def connect(self):
        await self.accept()
        await self._send_json({
            "connection": True
        })

    async def disconnect(self, close_code):
        await self._send_json({
            "connection": False
        })