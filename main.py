from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from src.banner import load_banner
from src.app import ArgusApp

console = Console()

#TODO: TUTORIAL on Textual
#TODO: Banner adapt to terminal length
TITLE: str = "PROJECT ARGUS"
START_COLOR = (0, 255, 255)  # cyan
END_COLOR = (255, 0, 255)  # magenta
DEBUG = True

def main():
    if not DEBUG:
        load_banner(TITLE, START_COLOR, END_COLOR, "ansi_shadow", "diagonal", (0.2 if not DEBUG else 0.0))

        console.print(Panel(
            "[pale_green1]:rocket: ARGUS LOADED SUCCESSFULLY[/pale_green1] \n" +
            "Enter [bold blink yellow]LAUNCH-ARGUS[/bold blink yellow] to start the Project...",
            border_style="sky_blue2",
            padding=(1, 5),
            title_align="center",
            expand=False,
        ), justify="center")

        while Prompt.ask(Text("Launch Code", justify="center", style="bold yellow")) != "LAUNCH-ARGUS" and not DEBUG:
            console.print("[bold blink red]WRONG INPUT![/bold blink red]")

    app = ArgusApp(debug_mode=DEBUG)
    app.run()


if __name__ == '__main__':
    main()
