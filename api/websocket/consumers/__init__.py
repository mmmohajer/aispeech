from websocket.consumers import test_socket, chat_bot, teacher, general_teacher, streaming

TestSocketConsumer = streaming.StreamingConsumer.as_asgi()

ChatBotConsumer = chat_bot.ChatBotConsumer.as_asgi()

TeacherConsumer = general_teacher.TeacherConsumer.as_asgi()