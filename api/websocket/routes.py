from django.urls import path, re_path

from . import consumers

URL_PATHS = [
    path("wss/test-socket/<room_id>/", consumers.TestSocketConsumer),
    path("wss/chat-bot/", consumers.ChatBotConsumer),
    path("wss/teacher/<room_id>/", consumers.TeacherConsumer),
    path("wss/translator/<room_id>/", consumers.TranslatorConsumer),
]
