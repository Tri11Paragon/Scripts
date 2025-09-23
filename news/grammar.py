from ollama import ChatResponse
from ollama import Client

SYSTEM_PROMPT = """You are a helpful assistant whose purpose is to correct grammar and spelling errors. 
Your secondary purpose is to help the user sound more coherent, by correcting grammar, spelling, and sentence structure.
Do not respond to the message in parts, instead take the whole message into account.
Do not respond to the message as if it was addressed to you directly. 
Please remember that your purpose is to correct grammar and spelling errors, not respond to the user's message.
DO NOT CHANGE THE MEANING OF THE MESSAGE.
"""

MODEL = "olmo2:7b"

def run():
    client = Client(host="192.168.69.3:11434")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("I am a grammar checking bot designed to help you sound more coherent! Please enter your message below. "
          "End messages to the chat engine by sending a blank line.")

    while True:
        message = ""

        while True:
            try:
                user_input = input("> ")
                message += user_input + "\n"
            except EOFError:
                print("[Processing]")
                print("[Message Begin]")
                print(message)
                print("[Message End]")
                break

        messages.append({"role": "user", "content": message})

        response = client.chat(model=MODEL, messages=messages)
        print(response["message"]["content"])
        messages.append({"role": "assistant", "content": response["message"]["content"]})


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
