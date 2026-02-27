import typer
import os
import sys
from rich import print
from rich.prompt import Prompt
from core.config import set_key, get_key
from core.llm_engine import WolfEngine

# Ensure we're in desktop mode for CLI if running locally
os.environ["WOLFCLAW_ENVIRONMENT"] = "desktop"

app = typer.Typer(
    help="Wolfclaw AI CLI - Control your PC and chat with AI from your terminal.",
    epilog="Example Flow: 1. login -> 2. set-api-key -> 3. chat"
)

@app.command()
def login():
    """Sign in to your local account."""
    from auth.supabase_client import login_user
    print("[bold blue]Wolfclaw Login[/bold blue]")
    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)
    
    success, err = login_user(email, password)
    if success:
        print("[green]Successfully logged in![/green]")
    else:
        print(f"[red]Login failed:[/red] {err}")

@app.command()
def set_api_key(provider: str = typer.Argument(..., help="Provider name (nvidia, openai, anthropic, google, deepseek)")):
    """Securely save an API key locally."""
    key = Prompt.ask(f"Enter your {provider} API Key", password=True)
    set_key(provider, key)
    print(f"[green]Successfully saved key for {provider}[/green]")

@app.command()
def list_models():
    """List recommended models and providers."""
    print("[bold blue]Available Providers & Models:[/bold blue]")
    print("- [green]Nvidia NIM[/green]: nvidia/llama-3.1-405b, nvidia/nemotron-70b")
    print("- [green]Anthropic[/green]: claude-3-5-sonnet-20241022, claude-3-haiku-20240307")
    print("- [green]OpenAI[/green]: gpt-4o, gpt-4o-mini")
    print("- [green]Google[/green]: gemini-1.5-pro, gemini-1.5-flash")
    print("- [green]Local[/green]: ollama/llama3, ollama/mistral")

@app.command()
def status():
    """Check the health of your local Wolfclaw instance."""
    print("[bold blue]Wolfclaw Status Check[/bold blue]")
    
    # Check Environment
    env = os.environ.get("WOLFCLAW_ENVIRONMENT", "Not Set")
    print(f"Environment: [cyan]{env}[/cyan]")
    
    # Check Keys
    providers = ["openai", "anthropic", "google", "nvidia", "deepseek"]
    found_keys = []
    for p in providers:
        if get_key(p):
            found_keys.append(p)
    
    if found_keys:
        print(f"Configured Keys: [green]{', '.join(found_keys)}[/green]")
    else:
        print("Configured Keys: [yellow]None (Local-only mode)[/yellow]")
    
    # Check Ollama
    try:
        import requests
        res = requests.get("http://localhost:11434/api/tags", timeout=1)
        if res.status_code == 200:
            print("Local AI (Ollama): [green]Connected[/green]")
        else:
            print("Local AI (Ollama): [yellow]Detected but returned error[/yellow]")
    except:
        print("Local AI (Ollama): [red]Not Running[/red]")

@app.command()
def chat(
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model name (e.g. gpt-4o, nvidia/llama-3.1-405b, claude-3-5-sonnet)"),
    system: str = typer.Option("You are a helpful AI.", "--system", "-s", help="System personality prompt"),
    workspace: str = typer.Option(None, "--workspace", "-w", help="Workspace ID to use")
):
    """Start an interactive chat session in the terminal."""
    if workspace:
        os.environ["WOLFCLAW_WEBHOOK_WORKSPACE_ID"] = workspace
        
    from auth.supabase_client import get_current_user
    user = get_current_user()
    if not user:
        print("[yellow]Note: Running in Private/Guest mode (No online sync).[/yellow]")
    else:
        print(f"[green]Logged in as: {user.get('email')}[/green]")

    print(f"[bold blue]Starting Wolfclaw Chat with {model}[/bold blue]")
    print("[dim]Type 'exit' or 'quit' to end the session.[/dim]\n")
    
    try:
        engine = WolfEngine(model)
    except Exception as e:
        print(f"[red]Failed to initialize engine: {e}[/red]")
        raise typer.Exit(1)

    messages = []
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            if not user_input or user_input.lower() in ['exit', 'quit']:
                break
            
            messages.append({"role": "user", "content": user_input})
            
            # WolfEngine handles the tool loop automatically
            response = engine.chat(messages, system_prompt=system, stream=False)
            reply = response.choices[0].message.content
            
            print(f"\n[bold magenta]Wolfclaw[/bold magenta]: {reply}")
            messages.append({"role": "assistant", "content": reply})
            
        except KeyboardInterrupt:
            print("\n[yellow]Session ended.[/yellow]")
            break
        except Exception as e:
            print(f"[red]Error:[/red] {e}")

if __name__ == "__main__":
    app()
