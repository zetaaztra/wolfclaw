import os
from litellm import completion
from core.config import get_key

os.environ["NVIDIA_API_KEY"] = get_key("nvidia")

try:
    response = completion(
        model="openai/meta/llama-3.1-70b-instruct",
        messages=[{"role": "user", "content": "hello"}],
        api_base="https://integrate.api.nvidia.com/v1",
        api_key=os.environ["NVIDIA_API_KEY"]
    )
    print("OPENAI COMPAT SUCCESS:", response.choices[0].message.content)
except Exception as e:
    print("OPENAI COMPAT ERROR:", e)

try:
    response = completion(
        model="nvidia_nim/meta/llama-3.1-70b-instruct",
        messages=[{"role": "user", "content": "hello"}],
        api_key=os.environ["NVIDIA_API_KEY"]
    )
    print("NVIDIA NIM NATIVE SUCCESS:", response.choices[0].message.content)
except Exception as e:
    print("NVIDIA NIM NATIVE ERROR:", e)
