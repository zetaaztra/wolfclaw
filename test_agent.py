from core.llm_engine import WolfEngine

print("Initializing Agentic Engine...")
# We use the Nvidia Llama 3.1 70B model which has excellent tool calling
engine = WolfEngine("nvidia/llama-3.1-70b-instruct")

messages = [
    {"role": "user", "content": "Can you run a command to tell me what files are in the current directory? Use your terminal tool."}
]

print("\nUser: ", messages[0]["content"])
print("\nLetting the AI think and interact with the OS...\n")

response = engine.chat(messages)

print("\nFinal AI Response:")
print(response.choices[0].message.content)
