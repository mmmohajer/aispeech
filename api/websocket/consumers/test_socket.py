# consumers/rooms.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

ROOMS = {}

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room = self.scope["url_route"]["kwargs"]["room"]
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

        # Track user in room
        if self.room not in ROOMS:
            ROOMS[self.room] = set()
        ROOMS[self.room].add(self.channel_name)

        # Tell this user how many are in the room
        await self.send(json.dumps({
            "type": "room_info",
            "count": len(ROOMS[self.room])
        }))

        # Notify others
        await self.channel_layer.group_send(
            self.room, {"type": "peer_joined", "sender": self.channel_name}
        )

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room, self.channel_name)
        if self.room in ROOMS:
            ROOMS[self.room].discard(self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Here you can handle chat messages, metadata, etc.
        await self.channel_layer.group_send(
            self.room, {"type": "chat_message", "data": data}
        )

    async def peer_joined(self, event):
        if event["sender"] != self.channel_name:
            await self.send(json.dumps({"type": "peer_joined"}))

    async def chat_message(self, event):
        await self.send(json.dumps(event["data"]))
