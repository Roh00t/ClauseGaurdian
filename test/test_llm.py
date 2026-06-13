from openai import OpenAI
client = OpenAI(
    api_key="sk-Kzv6ihVYCgyrws3xmG8pCS8xNUAnnDBRaWHTiWyCCGxx9dGi",
    base_url="https://api.tokenrouter.com/v1",
)
resp = client.chat.completions.create(
    model="moonshotai/kimi-k2.6",
    messages=[
        {"role": "system", "content": "Reply with valid JSON only: {\"ok\": true}"},
        {"role": "user", "content": "test"},
    ],
)
print(resp.choices[0].message.content)
