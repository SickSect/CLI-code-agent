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


@click.group()
@click.version_option("0.1.0", prog_name="codeagent")
def main() -> None:
    """CLI agent that writes, runs, checks, and fixes code locally with Ollama."""


@main.command()
@click.argument("task")
@click.option(
    "--exec/--no-exec",
    "allow_exec",
    default=False,
    help="Actually run the generated code in a sandbox (default: static check only).",
)
@click.option(
    "-n",
    "--iterations",
    default=5,
    show_default=True,
    help="Maximum number of review/fix iterations.",
)
@click.option(
    "-m",
    "--model",
    default=None,
    help="Override the model (otherwise taken from config/env).",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the final code to this file.",
)
@click.option(
    "--backend",
    type=click.Choice(["subprocess", "docker"]),
    default="subprocess",
    show_default=True)
@click.option("-q", "--quiet", is_flag=True, help="Suppress step-by-step logs.")
@click.option("-t", "--timeout", default=10, show_default=True,
              help="Seconds before a single execution is killed.")
def run(
        task: str,
        allow_exec: bool,
        iterations: int,
        model: str | None,
        output: Path | None,
        quiet: bool,
        backend: str,
        timeout: int
) -> None:
    """Generate, review and fix code for TASK."""
    # Creating the client here (a) lets us fail fast on a dead backend and
    # (b) seeds the module-level singleton that run_agent_loop() reuses, so a
    # --model override propagates into the loop. This coupling is intentional
    # for now and will be made explicit when the orchestrator is refactored.
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

    if output and state.code:
        output.write_text(state.code, encoding="utf-8")
        click.secho(f"\nSaved to {output}", fg="cyan")

    # Exit non-zero when the reviewer never approved, so the CLI is scriptable.
    raise SystemExit(0 if state.done else 2)


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


@main.command()
@click.option("--exec/--no-exec", "allow_exec", default=False,
              help="Actually run the generated code in a sandbox.")
@click.option("-n", "--iterations", default=5, show_default=True,
              help="Maximum number of review/fix iterations.")
@click.option("--backend", type=click.Choice(["subprocess", "docker"]),
              default="subprocess", show_default=True,
              help="Where to run the code.")
@click.option("-q", "--quiet", is_flag=True, help="Suppress step-by-step logs.")
@click.option("-t", "--timeout", default=10, show_default=True,
              help="Seconds before a single execution is killed.")
def chat(allow_exec, iterations, backend, quiet, timeout):
    """Interactive session: send tasks one by one; /save <path>, /exit."""
    last_state = None
    try:
        while True:
            user_input = click.prompt("codeagent", type=str).strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0]
                if cmd == "/exit":
                    break
                elif cmd == "/context":
                    if last_state and last_state.files_content:
                        click.echo(f"Context: {list(last_state.files_content)}")
                    else:
                        click.echo("Context is empty.")
                elif cmd == "/save":
                    if len(parts) < 2:
                        click.echo("Usage: /save <path>")
                    elif last_state is None or not last_state.files_content:
                        click.echo("Nothing to save yet - run a task first.")
                    else:
                        target_dir = Path(parts[1])
                        target_dir.mkdir(parents=True, exist_ok=True)
                        for path, content in last_state.files_content.items():
                            file_path = target_dir / path
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            file_path.write_text(content, encoding="utf-8")
                        click.secho(
                            f"Saved {len(last_state.files_content)} files to {target_dir}",
                            fg="cyan",
                        )
                elif cmd == "/new":
                    last_state = None
                    click.echo("Session context cleared.")
                else:
                    click.echo(f"Unknown command: {cmd}")
                continue

            try:
                last_state = run_agent_loop(
                    user_input,
                    allow_exec=allow_exec,
                    max_iterations=iterations,
                    backend=backend,
                    verbose=not quiet,
                    timeout=timeout,
                    last_state=last_state
                )
            except Exception as e:
                click.secho(f"Task failed: {e}", fg="red", err=True)
                continue
            click.echo(last_state.code or "(no code produced)")
    except (KeyboardInterrupt, EOFError):
        click.echo("\nBye!")


if __name__ == "__main__":
    main()
