from ollama import ChatResponse
from ollama import Client

SYSTEM_PROMPT = """You are a helpful assistant designed to correct grammar and spelling errors. 
Your secondary purpose is to help the user sound more coherent, preferably by correcting sentence structure.
The user will provide you with a message. You should respond with a corrected version of the message. 
You should include a list of changes you have made in your response message AFTER the corrected message.
You should NOT change the meaning of the message."""

MODEL = "llama3.2:3b"

def run():
    client = Client(host="192.168.69.3:11434")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("I am a grammar checking bot designed to help you sound more coherent! Please enter your message below. "
          "End messages to the chat engine by sending a blank line.")

    while True:
        message = ""

        while True:
            user_input = input("> ")
            if user_input.strip() == "":
                break
            else:
                message += user_input + "\n"

        messages.append({"role": "user", "content": message})

        response = client.chat(model=MODEL, messages=messages)
        print(response["message"]["content"])
        messages.append({"role": "assistant", "content": response["message"]["content"]})


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
