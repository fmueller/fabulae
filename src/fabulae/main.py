"""Fabulae CLI application."""

import typer

from fabulae.version_cli import version_command

app = typer.Typer(
    help="Fabulae — your CLI application.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def app_callback(ctx: typer.Context) -> None:
    """Root callback invoked when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


app.command(name="version", help="Display the current version.")(version_command)


def main() -> None:
    """Entry point for the fabulae CLI."""
    app()


if __name__ == "__main__":
    main()
