"""Command-line interface for codeagent.

This module provides the ``codeagent`` console script declared in
``pyproject.toml`` (``[project.scripts] codeagent = "codeagent.cli:main"``).
It is a thin Click wrapper around :func:`codeagent.orchestrator.run_agent_loop`
plus a couple of helper commands for inspecting the local Ollama backend.
"""

from pathlib import Path

import click

from codeagent.client import get_client
from codeagent.orchestrator import run_agent_loop


# --------------------------------------------------------------------------
# Shared option set
# --------------------------------------------------------------------------

def common_run_options(func):
    """Attach the options that `run` and `chat` both accept.

    click.option(...) does not decorate anything by itself: calling it returns
    a decorator. So the list below holds ready-made decorators, and the loop
    applies them one by one — exactly what stacking @click.option lines does.

    reversed() keeps the order: a decorator stack is applied bottom-up, so
    without it the flags would show up backwards in --help.
    """
    options = [
        click.option(
            "--exec/--no-exec", "allow_exec", default=False,
            help="Actually run the generated code in a sandbox "
                 "(default: static check only).",
        ),
        click.option(
            "-n", "--iterations", default=5, show_default=True,
            help="Maximum number of review/fix iterations.",
        ),
        click.option(
            "--backend", type=click.Choice(["subprocess", "docker"]),
            default="subprocess", show_default=True,
            help="Where to run the code.",
        ),
        click.option(
            "-t", "--timeout", default=10, show_default=True,
            help="Seconds before a single execution is killed.",
        ),
        click.option("-q", "--quiet", is_flag=True, help="Suppress step-by-step logs."),
    ]
    for option in reversed(options):
        func = option(func)
    return func


# --------------------------------------------------------------------------
# Small helpers shared by the commands
# --------------------------------------------------------------------------

def _require_backend(client) -> None:
    """Abort with a clear message if Ollama or the model is unavailable.

    Called before any command that actually talks to the model, so the user
    sees a one-line hint instead of a stack trace raised deep inside the loop.
    """
    if not client.is_running():
        click.secho(
            "Ollama is not running. Start it with:  ollama serve",
            fg="red",
            err=True,
        )
        raise SystemExit(1)
    if not client.is_model_available():
        click.secho(
            f"Model '{client.model}' is not available. Pull it with:  "
            f"ollama pull {client.model}",
            fg="red",
            err=True,
        )
        raise SystemExit(1)


def _warn_if_unvalidated(state) -> None:
    """Tell the user when the code was never checked.

    validated=False means there was no toolchain (or no validator) for that
    language — not that the code is wrong. So this is a warning, not an error,
    and the code is still shown.
    """
    if state.validated:
        return
    click.secho(
        "Warning: this code was NOT statically validated and was not executed — "
        "it may contain syntax errors.",
        fg="yellow",
    )
    if state.validation_note:
        click.secho(f"  Reason: {state.validation_note}", fg="yellow")


def _write_files_to(files_content: dict, target_dir: Path) -> None:
    """Write every generated file into target_dir, creating folders as needed."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for path, content in files_content.items():
        file_path = target_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)  # nested paths, e.g. app/x.py
        file_path.write_text(content, encoding="utf-8")
    click.secho(f"Saved {len(files_content)} files to {target_dir}", fg="cyan")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

@click.group()
@click.version_option("0.1.0", prog_name="codeagent")
def main() -> None:
    """CLI agent that writes, runs, checks, and fixes code locally with Ollama."""


@main.command()
@click.argument("task")
@common_run_options
@click.option(
    "-m", "--model", default=None,
    help="Override the model (otherwise taken from config/env).",
)
@click.option(
    "-o", "--output",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Write all generated files to this directory.",
)
def run(
        task: str,
        allow_exec: bool,
        iterations: int,
        backend: str,
        timeout: int,
        quiet: bool,
        model: str | None,
        output: Path | None,
) -> None:
    """Generate, review and fix code for TASK."""
    # Creating the client here (a) lets us fail fast on a dead backend and
    # (b) seeds the module-level singleton that run_agent_loop() reuses, so a
    # --model override propagates into the loop.
    client = get_client(model=model)
    _require_backend(client)

    state = run_agent_loop(
        task,
        allow_exec=allow_exec,
        max_iterations=iterations,
        verbose=not quiet,
        backend=backend,
        timeout=timeout,
    )

    click.echo()
    click.secho("===== FINAL CODE =====", fg="green", bold=True)
    click.echo(state.code or "(no code produced)")
    _warn_if_unvalidated(state)

    if output and state.files_content:
        _write_files_to(state.files_content, output)

    # Exit non-zero when the reviewer never approved, so the CLI is scriptable.
    raise SystemExit(0 if state.done else 2)


@main.command()
@common_run_options
def chat(allow_exec, iterations, backend, timeout, quiet):
    """Interactive session: /save <path>, /context, /new, /exit."""
    last_state = None
    try:
        while True:
            user_input = click.prompt("codeagent", type=str).strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                _handle_command(user_input, last_state)
                if user_input.split(maxsplit=1)[0] == "/exit":
                    break
                if user_input.split(maxsplit=1)[0] == "/new":
                    last_state = None
                continue  # a command never reaches the model

            try:
                last_state = run_agent_loop(
                    user_input,
                    allow_exec=allow_exec,
                    max_iterations=iterations,
                    backend=backend,
                    verbose=not quiet,
                    timeout=timeout,
                    last_state=last_state,
                )
            except Exception as e:
                click.secho(f"Task failed: {e}", fg="red", err=True)
                continue

            click.echo(last_state.code or "(no code produced)")
            _warn_if_unvalidated(last_state)
    except (KeyboardInterrupt, EOFError):
        click.echo("\nBye!")


def _handle_command(user_input: str, last_state) -> None:
    """Run one /slash command. Session state is reset by the caller."""
    parts = user_input.split(maxsplit=1)
    cmd = parts[0]

    if cmd == "/exit":
        return

    if cmd == "/new":
        click.echo("Session context cleared.")
        return

    if cmd == "/context":
        if last_state and last_state.files_content:
            click.echo(f"Context: {list(last_state.files_content)}")
        else:
            click.echo("Context is empty.")
        return

    if cmd == "/save":
        if len(parts) < 2:
            click.echo("Usage: /save <path>")
        elif last_state is None or not last_state.files_content:
            click.echo("Nothing to save yet - run a task first.")
        else:
            _write_files_to(last_state.files_content, Path(parts[1]))
        return

    click.echo(f"Unknown command: {cmd}")


@main.command()
def models() -> None:
    """List models available in the local Ollama instance."""
    client = get_client()
    if not client.is_running():
        click.secho(
            "Ollama is not running. Start it with:  ollama serve",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    available = client.list_available_models()
    if not available:
        click.echo("No models downloaded.")
        return
    for name in available:
        # Mark the currently configured default model with an asterisk.
        marker = "*" if name == client.model else " "
        click.echo(f"{marker} {name}")


@main.command()
def doctor() -> None:
    """Check that Ollama is reachable and the configured model is present."""
    client = get_client()
    running = client.is_running()

    click.echo(f"Host:    {client.host}")
    click.echo(f"Model:   {client.model}")
    click.secho(f"Running: {running}", fg="green" if running else "red")

    if not running:
        click.echo("Start it with:  ollama serve")
        return

    ok = client.is_model_available()
    click.secho(f"Model available: {ok}", fg="green" if ok else "red")
    if not ok:
        click.echo(f"Pull it with:  ollama pull {client.model}")


if __name__ == "__main__":
    main()