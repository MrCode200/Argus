import time
from itertools import cycle

from pyfiglet import Figlet, FigletString
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from typing_extensions import Literal


def split_text_to_console_lines(text: str, letter_width: int, text_max_chars: int | None = None) -> list[str]:
    """
    Split `text` into lines suitable for printing with pyfiglet in a console.

    - `letter_width` is how many console columns one figlet character approximately occupies.
      The maximum characters per line is computed as Console().width / letter_width.
    - Long words that exceed the line width are split into chunks. Every chunk except the final
      one ends with '-' to indicate continuation.
    - Words that fit together (with a single space between them) are combined on the same line.

    `test_max_chars` (optional) lets you override calculated line width for testing.
    """
    max_chars = text_max_chars if text_max_chars is not None else max(1, int(Console().width / letter_width))

    def _split_long_word_to_chunks(word: str, width: int) -> list[str]:
        chunks: list[str] = []
        w = word
        while len(w) > width:
            chunk = w[: width - 1] + "-"
            chunks.append(chunk)
            w = w[width - 1:]
        chunks.append(w)
        return chunks

    words = text.split()
    result: list[str] = []
    current_line: str = ""

    for word in words:
        space_needed = 1 if current_line else 0
        available_space = max_chars - len(current_line) - space_needed

        # 1) fits in current line
        if len(word) <= available_space:
            current_line += (" " if current_line else "") + word

        # 2) doesn't fit in current line but fits on empty line
        elif len(word) <= max_chars:
            if current_line:
                result.append(current_line)
            current_line = word

        # 3) too long: split into chunks
        else:
            if current_line:
                result.append(current_line)
                current_line = ""
            chunks = _split_long_word_to_chunks(word, max_chars)
            result.extend(chunks[:-1])
            current_line = chunks[-1]

    if current_line:
        result.append(current_line)

    return result


def generate_gradient_color(
        start_color: tuple[int, int, int],
        end_color: tuple[int, int, int],
        steps: int
) -> list[tuple[int, ...]]:
    if steps <= 1:
        return [start_color]

    gradient_color = []
    for t in range(steps):
        ratio = t / (steps - 1)

        rgb = tuple(
            int(start_color[i] + (end_color[i] - start_color[i]) * ratio)
            for i in range(3)
        )
        gradient_color.append(rgb)
    return gradient_color


def create_banner(
        text: str,
        figlet_font: str,
        start_color: tuple[int, int, int],
        end_color: tuple[int, int, int],
        interpolate_direction: Literal["vertical", "horizontal", "diagonal"] = "vertical",
        padding_width: int = 1,
) -> Text:
    """
    :param text: The text to be rendered.
    :param figlet_font: The font to be used for rendering.
    :param start_color: The starting color of the gradient.
    :param end_color: The ending color of the gradient.
    :param interpolate_direction: Whether to interpolate vertically or horizontally or diagonally.
    :param padding_width: The width of the padding to be added to the text.
    """
    def rgb_to_hex(rgb) -> str:
        """Convert (R,G,B) to hex string usable by rich, like '#ff00ff'."""
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    f = Figlet(font=figlet_font)

    avg_char_length: int = int(
        sum([len(f.renderText(c).splitlines()[0]) for c in text]) / len(text)) + 1 + padding_width
    split_text: list[str] = split_text_to_console_lines(text, avg_char_length)

    orig_text = text
    text = ""
    for line in split_text:
        if line.endswith("-"):
            text += line
        else:
            text += line + " "

    # List[char[pixels_per_height]]
    ascii_chars: list[list[FigletString]] = [f.renderText(ch).splitlines() for ch in text]
    char_height = max(len(char) for char in ascii_chars)

    if interpolate_direction == "horizontal":
        color_steps = max(len(text), len(orig_text))
    elif interpolate_direction == "vertical":
        color_steps = len(split_text) * char_height
    else:
        color_steps = len(text) + char_height + len(split_text) - 2
    hex_colors: list[str] = [rgb_to_hex(rgb) for rgb in generate_gradient_color(start_color, end_color, color_steps)]

    banner = Text()
    char_pos = 0
    for line_num, text_line in enumerate(split_text):
        formatted_text_line = Text(justify="center")

        for h in range(char_height):
            pixel_line = Text()

            for i, c in enumerate(ascii_chars[char_pos:(len(text_line)) + char_pos]):
                if interpolate_direction == "horizontal":
                    color = hex_colors[i + char_pos]
                elif interpolate_direction == "vertical":
                    color = hex_colors[h + line_num * char_height]
                else:
                    color = hex_colors[(h + line_num) + (i + char_pos)]

                pixel_line.append(Text(c[h], style=color))
            formatted_text_line.append(pixel_line + "\n")

        banner += formatted_text_line
        # +1 as line ends with space (which is contained in ascii_char but not in split_text)
        # Normal if ends with - as this is contained in split_text
        char_pos += len(text_line) + 1 if not text_line.endswith("-") else len(text_line)

    return banner


def load_banner(
        title: str,
        start_color: tuple[int, int, int],
        end_color: tuple[int, int, int],
        figlet_font: str,
        interpolate_direction: Literal["vertical", "horizontal", "diagonal"] = "vertical",
        sleep_time: float = 0.2,
):
    console = Console()
    with Progress(
            SpinnerColumn(spinner_name="moon"),  # spinner animation
            TextColumn("{task.description}", justify="center"),
            console=console,
            transient=True,
            disable=True,
    ) as progress:
        total_steps = len(title)
        task = progress.add_task("Loading")

        dot_cycle = cycle([".", "..", "..."])
        for i in range(total_steps):
            console.clear()

            dots = next(dot_cycle)
            progress.update(task, description=f"[bold yellow]Loading{dots}")

            text = title[:i + 1] + (" " * (len(title) - (i + 1)))
            banner = create_banner(text, figlet_font, start_color, end_color, interpolate_direction)
            console.print(Align.center(banner))
            console.print("\n")

            if i != total_steps - 1:
                console.print(Align.center(progress.get_renderable()))

            time.sleep(sleep_time)


if __name__ == '__main__':
    console = Console()

    TITLE: str = "Leonas Wenn du kannst Programmieren nicht vergessen ;))"
    START_COLOR = (0, 255, 255)  # cyan
    END_COLOR = (255, 0, 255)  # magenta
    load_banner(TITLE, START_COLOR, END_COLOR, "ansi_shadow", "horizontal", 0.25)  # 2)

    console.print(Panel(
        "[pale_green1]:rocket: ARGUS LOADED SUCCESSFULLY[/pale_green1] \n" +
        "Press [bold blink yellow]ENTER[/bold blink yellow] to start the Project...",
        border_style="sky_blue2",
        padding=(1, 5),
        title_align="center",
        expand=False,
    ), justify="center")
