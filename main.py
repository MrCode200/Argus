from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from src.banner import load_banner
from src.app import ArgusApp
from config.settings import settings

console = Console()

#TODO: TUTORIAL on Textual
#TODO: Banner adapt to terminal length
TITLE: str = "PROJECT ARGUS"
LAUNCH_CODE: str = "LAUNCH-ARGUS67"
START_COLOR = (0, 255, 255)  # cyan
END_COLOR = (255, 0, 255)  # magenta

def main():
    load_banner(TITLE, START_COLOR, END_COLOR, "ansi_shadow", "diagonal",
                (0.2 if not settings.config_dev.get_value("skip_banner_animation") else 0.0))

    if not settings.config_dev.get_value("skip_launch_code_prompt"):
        console.print(Panel(
            "[pale_green1]:rocket: ARGUS LOADED SUCCESSFULLY[/pale_green1] \n" +
            f"Enter [bold blink yellow]{LAUNCH_CODE}[/bold blink yellow] to start the Project...",
            border_style="sky_blue2",
            padding=(1, 5),
            title_align="center",
            expand=False,
        ), justify="center")

        while Prompt.ask(Text("Launch Code", justify="center", style="bold yellow")) != LAUNCH_CODE:
            console.print("[bold blink red]WRONG INPUT![/bold blink red]")

    app = ArgusApp()
    app.run()


if __name__ == '__main__':
    main()
