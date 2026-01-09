import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Prompt
from rich.text import Text

console = Console()

TITLE = "PROJECT ARGUS"
LAUNCH_CODE = "LAUNCH-ARGUS67"
START_COLOR = (0, 255, 255)
END_COLOR = (255, 0, 255)


# Step 1: logger comes first
def init_logger():
    from magic_utils import setup_logger  # delayed import, avoids premature logging
    from src.utils.loggingRichLog import LogBufferHandler

    logger = setup_logger(
        logger_name="argus.app",
        log_file_path=str(Path("./logs/log.jsonl").resolve()),
        log_in_json=True,
        stream_formatter=None,
        stream_in_color=False,
    )
    logger.addHandler(LogBufferHandler())
    return logger


# Step 2: environment
def ensure_api_key():
    from src.validation import validate_locationiq_key

    load_dotenv()
    if os.getenv("LOCATIONIQ_API_KEY"):
        return

    console.print(Panel.fit(
        "LocationIQ API Key Required",
        border_style="blue",
        padding=(1, 2),
    ))

    while True:
        key = Prompt.ask("Enter your LocationIQ API key", password=True, console=console)
        if validate_locationiq_key(key):
            break
        console.print("Invalid API key. Try again.", style="bold red")

    with open(".env", "w") as f:
        f.write(f"LOCATIONIQ_API_KEY={key}")

    os.environ["LOCATIONIQ_API_KEY"] = key
    console.print("[green]API key saved. Continuing...[/]")


# Step 3: create filesystem
def create_missing_files_and_folders(logger: logging.Logger, settings):
    for path in ("./ephemerises", "./assets/interstellarObjectImages", "./logs", "./assets/locationImages"):
        p = Path(path)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            console.print(f"Created directory: {path}", style="bold green")
            logger.debug(f"Created directory {path}")

    STATE_JSON = """
{
  "last_address": "",
  "last_ephemeris_file": "",
  "last_celestial_body": ""
}
    """

    if not os.path.exists("./config/state.json"):
        logger.debug("State file does not exist, creating...")
        with open("./config/state.json", "w") as f:
            f.write(STATE_JSON)

    if not os.path.exists("./config/config.json"):
        logger.debug("Settings file does not exist, creating...")
        settings.save()


# Step 4: prompt
def require_launch_code(settings):
    if settings.dev.get_value("skip_launch_code_prompt"):
        return

    console.print(Panel(
        f"[pale_green1]:rocket: ARGUS LOADED SUCCESSFULLY[/pale_green1] \n"
        f"Enter [bold blink yellow]{LAUNCH_CODE}[/bold blink yellow] to start",
        border_style="sky_blue2",
        padding=(1, 5),
    ), justify="center")

    while Prompt.ask(
            Text("Launch Code", justify="center", style="bold blink yellow")
    ) != LAUNCH_CODE:
        console.print("[bold blink red]WRONG INPUT![/bold blink red]")


def main():
    with Progress(
            TextColumn("{task.description}"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Initializing...", total=5)

        progress.update(task, description="Initializing logger...", advance=1)
        logger = init_logger()

        progress.update(task, description="Checking API key...", advance=1)
        ensure_api_key()

        progress.update(task, description="Loading configuration...", advance=1)
        # defer config & app imports until logger is alive
        from config.config import settings
        from src.banner import load_banner
        from src.app import ArgusApp

        progress.update(task, description="Creating directories and files...", advance=1)
        create_missing_files_and_folders(logger, settings)

        progress.update(task, description="✅ Finished Setup", advance=1)
        time.sleep(1)

    load_banner(
        TITLE, START_COLOR, END_COLOR, "ansi_shadow", "diagonal",
        (0.2 if not settings.dev.get_value("skip_banner_animation") else 0.0),
    )

    require_launch_code(settings)

    logger.info(f"Starting {TITLE}...")
    ArgusApp().run()


if __name__ == "__main__":
    main()
