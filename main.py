# main.py

import asyncio
from assistant_engine import AssistantEngine


async def main():

    assistant = AssistantEngine()

    while True:

        user_input = input("\nYOU: ")

        if user_input.lower() in ["exit", "quit"]:

            break

        response = await assistant.run_once(user_input)

        print(f"\nJARVIS: {response}")


if __name__ == "__main__":

    asyncio.run(main())