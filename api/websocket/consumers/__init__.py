from websocket.consumers import test_socket, chat_bot, teacher, general_teacher, translator

TestSocketConsumer = test_socket.TestSocketConsumer.as_asgi()

ChatBotConsumer = chat_bot.ChatBotConsumer.as_asgi()

TeacherConsumer = general_teacher.TeacherConsumer.as_asgi()

TranslatorConsumer = translator.TranslateConsumer.as_asgi()