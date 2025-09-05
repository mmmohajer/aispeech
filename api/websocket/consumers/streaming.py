# consumers/streaming.py
from channels.generic.websocket import AsyncWebsocketConsumer
from collections import defaultdict
import json

ROOM_MEMBERS = defaultdict(set)  # room -> set(channel_name)

class StreamingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room = self.scope["url_route"]["kwargs"]["room"]

        first_joiner = len(ROOM_MEMBERS[self.room]) == 0
        ROOM_MEMBERS[self.room].add(self.channel_name)

        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()

        # Tell this client its role
        await self.send(json.dumps({"type": "role", "role": "offerer" if first_joiner else "answerer"}))

        # Notify room about the current count and that someone joined
        count = len(ROOM_MEMBERS[self.room])
        await self.channel_layer.group_send(
            self.room, {"type": "room_signal", "data": {"type": "room_info", "count": count}}
        )
        await self.channel_layer.group_send(
            self.room, {"type": "room_signal", "data": {"type": "peer_joined"}}
        )

    async def disconnect(self, code):
        ROOM_MEMBERS[self.room].discard(self.channel_name)
        await self.channel_layer.group_discard(self.room, self.channel_name)

        count = len(ROOM_MEMBERS[self.room])
        await self.channel_layer.group_send(
            self.room, {"type": "room_signal", "data": {"type": "room_info", "count": count}}
        )

    async def receive(self, text_data):
        # Relay payload AS-IS (includes clientId if you send it) to everyone in room
        data = json.loads(text_data)
        await self.channel_layer.group_send(self.room, {"type": "signal", "data": data})

    async def signal(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def room_signal(self, event):
        await self.send(text_data=json.dumps(event["data"]))
