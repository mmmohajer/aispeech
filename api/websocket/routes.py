from django.urls import path, re_path

from . import consumers

URL_PATHS = [
    # path("wss/test-socket/", consumers.TestSocketConsumer),
    re_path(r"wss/test-socket/(?P<room>\w+)/$", consumers.TestSocketConsumer),
    path("wss/chat-bot/", consumers.ChatBotConsumer),
    path("wss/teacher/", consumers.TeacherConsumer),
]
