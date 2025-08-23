from websocket.consumers import test_socket, chat_bot

TestSocketConsumer = test_socket.TestSocketConsumer.as_asgi()

ChatBotConsumer = chat_bot.ChatBotConsumer.as_asgi()