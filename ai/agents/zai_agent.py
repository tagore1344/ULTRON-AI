import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url="https://api.z.ai/api/paas/v4/"
)


def ask_zai(prompt):

    try:

        response = client.chat.completions.create(

            model="glm-4.5",

            messages=[
                {
                    "role": "system",
                    "content": "You are ULTRON AI."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

        )

        return response.choices[0].message.content

    except Exception as e:

        return str(e)