import typer

app = typer.Typer()

@app.command()
def main():
    """
    Main entry point for the TCP Optimizer CLI.
    """
    typer.echo("TCP Optimizer CLI is running.")

if __name__ == "__main__":
    app()