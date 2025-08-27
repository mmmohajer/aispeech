from channels.generic.websocket import AsyncWebsocketConsumer
import json
import functools
import asyncio
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs
from asgiref.sync import sync_to_async

from core.models import UserModel

class BaseConsumer(AsyncWebsocketConsumer):

    async def _send_json(self, data):
        await self.send(text_data=json.dumps(data))

    async def _send_bytes(self, data):
        await self.send(bytes_data=data)
    
    async def _run_blocking(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    
    async def _handle_error(self, message):
        return await self._send_json({"error": message})
    
    async def connect(self):
        await self.accept()
        return await self._send_json({
            "connection": True
        })

    async def disconnect(self, close_code):
        return await self._send_json({
            "connection": False
        })

class BasePrivateConsumer(BaseConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
    
    async def connect(self):
        query_string = self.scope['query_string'].decode()
        token = parse_qs(query_string).get('token', [None])[0]
        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                self.user = await sync_to_async(UserModel.objects.get)(id=user_id)
                await self.accept()
                await self._send_json({
                    "connection": True,
                    "email": self.user.email
                })
            except Exception as e:
                await self._send_json({
                    "connection": False,
                })
                return await self._handle_error(f"{e}")