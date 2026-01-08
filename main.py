# --- IMPORTANT IMPORT (WHERE ORDER MATTERS) ---
import os
from pathlib import Path

import requests.exceptions
from dotenv import load_dotenv
from magic_utils import setup_logger
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

logger = setup_logger(
    logger_name="argus.app",
    log_file_path=str(Path("./logs/log.jsonl").resolve()),
    log_in_json=True,

    stream_formatter=None,
    stream_in_color=False
)

# Check for API Key
load_dotenv()

from src.locator.mapping import generate_map
if os.getenv("LOCATIONIQ_API_KEY") in (None, ""):
    console = Console()
    console.print(Panel.fit(
        "[bold cyan]🔑 LocationIQ API Key Required[/]",
        border_style="blue",
        padding=(1, 2)
    ))

    console.print("To use this application, you need a LocationIQ API key.")
    console.print("1. Get a free API key from [link=https://locationiq.com/]https://locationiq.com/[/]")
    console.print("2. Enter it below (it will be saved in your .env file)\n")
    console.print("3. Ask the CREATOR (MrCode200) for temp. key! ( ◡̀ ᴗ ◡́)و\n")

    #TODO: move Validation to seperate file, and add it to EnvSettings!
    while True:
        key = Prompt.ask(
            "Enter your LocationIQ API key",
            password=True,  # Hide the key while typing
            console=console
        )
        try:
            generate_map(key, 53.2845324, 10.5339104, [(53.2845324, 10.5339104)])
            break
        except requests.exceptions.HTTPError as e:
            console.print(f"Invalid API key. Please try again. 💥╾━╤デ╦︻ඞා", style="bold red")

    # Save to .env file
    with open(".env", "w") as f:
        f.write(f"LOCATIONIQ_API_KEY={key}")

    os.environ["LOCATIONIQ_API_KEY"] = key
    console.print("\n[green]✓ API key saved successfully! ₍ᐢ•⩊•ᐢ₎♡ ༘[/]")
    console.print("The application will now start. \n")

# ----------------------------------------------------------------
from config.config import settings
from src.app import ArgusApp
from src.banner import load_banner

console = Console()

TITLE: str = "PROJECT ARGUS"
LAUNCH_CODE: str = "LAUNCH-ARGUS67"
START_COLOR = (0, 255, 255)  # cyan
END_COLOR = (255, 0, 255)  # magenta


def main():
    logger.debug(f"Creating missing directories...")
    if Path("./ephemerises").mkdir(exist_ok=True):
        console.print("Ephemerises directory created!", style="bold green")
    if Path("./assets/interstellarObjectImages").mkdir(exist_ok=True):
        console.print("Interstellar Object Images directory created!", style="bold green")

    load_banner(TITLE, START_COLOR, END_COLOR, "ansi_shadow", "diagonal",
                (0.2 if not settings.dev.get_value("skip_banner_animation") else 0.0))

    if not settings.dev.get_value("skip_launch_code_prompt"):
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

    logger.info(f"Starting {TITLE}...")
    app = ArgusApp()
    app.run()


if __name__ == '__main__':
    main()
