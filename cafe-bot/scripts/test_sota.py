import sys
import os

# Ensure app is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.features.cafe_chatbot.chatbot import CafeChatbot

def main():
    bot = CafeChatbot()
    print("\n✅ Bot Ready! (Type 'quit' to exit)\n")

    while True:
        user_input = input("\033[1mYou:\033[0m ") # Bold 'You'
        
        if user_input.lower() in ["quit", "exit"]:
            print("Bye!")
            break

        print("\033[1mBot:\033[0m ", end="", flush=True)

        # Iterate over the stream
        for chunk in bot.chat_stream(user_input):
            # Print without newline, flush immediately to simulate typing
            print(chunk, end="", flush=True)
        
        print("\n") # Newline after response is done

if __name__ == "__main__":
    main()