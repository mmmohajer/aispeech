from channels.generic.websocket import AsyncWebsocketConsumer
import json

class BaseConsumer(AsyncWebsocketConsumer):

    async def _send_json(self, data):
        await self.send(text_data=json.dumps(data))

    async def _send_bytes(self, data):
        await self.send(bytes_data=data)
    
    async def connect(self):
        await self.accept()
        await self._send_json({
            "connection": True
        })

    async def disconnect(self, close_code):
        await self._send_json({
            "connection": False
        })