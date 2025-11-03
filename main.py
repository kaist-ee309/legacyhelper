import os
from legacyhelper.core.agent import Agent

def main():
    # For demonstration purposes, we'll set the API key here.
    # In a real application, you would use a more secure method.
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if gemini_api_key is None:
        print("Please set the GEMINI_API_KEY environment variable.")
        return

    agent = Agent()
    agent.run("Suggest a command to check the disk space on a Linux system.")

if __name__ == "__main__":
    main()