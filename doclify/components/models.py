from groq import APIError
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from doclify.schema.schema import LLMConfig
from doclify.utils.llm import create_client

console = Console()


def list_models():
    """Fetches and displays all available models from Groq in a rich table."""
    try:
        with create_client(LLMConfig()) as client:
            models_response = client.models.list()

        # Sort models alphabetically by Developer, then by Model ID
        models_sorted = sorted(
            models_response.data,
            key=lambda model: (
                str(getattr(model, "owned_by", "Unknown") or "Unknown").lower(),
                str(getattr(model, "id", "")).lower(),
            ),
        )

        # Build a beautiful Rich table
        table = Table(
            title_style="bold magenta",
            border_style="blue",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Model ID", justify="left", style="white")
        table.add_column("Developer", justify="left", style="green")
        table.add_column("Context", justify="right", style="yellow")
        table.add_column("Max Output", justify="right", style="cyan")

        for md in models_sorted:
            # Format token numbers into 'k' format for easier reading
            ctx = getattr(md, "context_window", None)
            ctx_str = f"{ctx // 1024}k" if ctx and ctx >= 1024 else str(ctx or "N/A")

            out = getattr(md, "max_completion_tokens", None)
            out_str = f"{out // 1024}k" if out and out >= 1024 else str(out or "N/A")

            table.add_row(
                escape(str(getattr(md, "id", "Unknown"))),
                escape(str(getattr(md, "owned_by", "Unknown"))),
                ctx_str,
                out_str,
            )

        console.print()
        console.print(table)

    except APIError:
        raise ValueError(
            "Groq model listing failed; verify local credentials and connectivity"
        ) from None
