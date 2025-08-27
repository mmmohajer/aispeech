from websocket.consumers import test_socket, chat_bot, teacher

TestSocketConsumer = test_socket.TestSocketConsumer.as_asgi()

ChatBotConsumer = chat_bot.ChatBotConsumer.as_asgi()

TeacherConsumer = teacher.TeacherConsumer.as_asgi()