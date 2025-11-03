from legacyhelper.model.gemini import GeminiModel
from rich.console import Console
from rich.prompt import Prompt

class Agent:
    def __init__(self):
        self.model = GeminiModel()
        self.console = Console()

    def run(self, prompt: str):
        response = self.model.get_response(prompt)
        
        # For now, we'll just present the response as a choice.
        # In the future, we will parse the response to extract commands.
        self.console.print("Proposed command:")
        self.console.print(f"[bold green]{response}[/bold green]")
        
        choice = Prompt.ask("Execute command?", choices=["y", "n"], default="n")
        
        if choice == "y":
            # We'll implement command execution in the next step.
            self.console.print("Executing command...")
        else:
            self.console.print("Command not executed.")