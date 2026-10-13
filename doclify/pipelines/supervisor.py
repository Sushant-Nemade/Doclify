import json
from functools import wraps

import click
from pydantic import ValidationError

from doclify import __version__
from doclify.components.init import init_project


class SafeGroup(click.Group):
    def invoke(self, context):
        try:
            return super().invoke(context)
        except ValidationError:
            raise click.ClickException("Configuration contains invalid fields or limits") from None
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        except (OSError, UnicodeError):
            raise click.ClickException(
                "Filesystem operation failed; inspect permissions and preserve existing files"
            ) from None


def legal_notice(context, parameter, value):
    if value and not context.resilient_parsing:
        click.echo(
            "Doclify by Hema Kalyan. Modified by Sushant Nemade on 2026-10-13.\nGNU AGPLv3; no warranty.\nSource: https://github.com/Sushant-Nemade/doclify\nLicense: https://github.com/Sushant-Nemade/doclify/blob/main/LICENSE"
        )
        context.exit()


@click.group(cls=SafeGroup)
@click.version_option(version=__version__)
@click.option(
    "--license",
    is_flag=True,
    is_eager=True,
    expose_value=False,
    callback=legal_notice,
    help="Show attribution, license and source availability.",
)
def cli():
    """Generate reviewable project documentation without executing repository code."""
    pass


@cli.command()
def init():
    """Discover source files and safely create or refresh doclify.yaml."""
    config = init_project()
    click.echo(
        f"Initialized doclify.yaml with {len(config.structure)} files. Review the manifest before running."
    )


@cli.group(name="set")
def set_group():
    """Change validated project configuration."""
    pass


@set_group.command("default")
@click.argument("model")
def set_default(model):
    """Set the default Groq model identifier."""
    from doclify.components.config import update_config

    update_config(model=model)
    click.echo("Default model updated.")


def generation_options(command):
    @wraps(command)
    def wrapped(*args, offline=False, provider=None, **kwargs):
        if offline and provider not in {None, "offline"}:
            raise click.UsageError("--offline conflicts with the selected provider")
        return command(*args, provider="offline" if offline else provider, **kwargs)

    options = [
        click.option("--model", help="Override the configured model for this run."),
        click.option("--provider", type=click.Choice(["groq", "offline"])),
        click.option(
            "--offline", is_flag=True, help="Use deterministic structural summaries, not AI."
        ),
        click.option(
            "--dry-run",
            is_flag=True,
            help="Preflight inputs and budgets without network calls or writes.",
        ),
        click.option(
            "--allow-upload",
            is_flag=True,
            help="Explicitly allow selected source code to be sent to Groq.",
        ),
    ]
    for option in options:
        wrapped = option(wrapped)
    return wrapped


@cli.command()
@generation_options
def run(**options):
    """Summarize stale files and generate a private README draft."""
    from doclify.pipelines.documentation import run_docs

    click.echo(json.dumps(run_docs(**options), indent=2))


@cli.command()
@click.argument("path")
@generation_options
def update(path, **options):
    """Refresh changed manifest files in PATH, then generate a draft; '.' selects all."""
    from doclify.pipelines.documentation import run_docs

    click.echo(json.dumps(run_docs(target=path, **options), indent=2))


@cli.command()
@click.option("--approve", required=True, help="Full SHA-256 digest of the inspected draft.")
@click.option(
    "--replace-readme",
    is_flag=True,
    help="Back up and replace README.md instead of writing README.generated.md.",
)
def publish(approve, replace_readme):
    """Publish an explicitly reviewed draft, verifying its digest first."""
    from doclify.pipelines.documentation import publish_readme

    click.echo(json.dumps(publish_readme(approve, replace_readme=replace_readme), indent=2))


@cli.command()
def models():
    """Explicitly contact Groq to list models; requires a locally configured key."""
    from doclify.components.models import list_models

    list_models()
