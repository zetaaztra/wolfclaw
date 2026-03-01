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


# --- Flow Commands ---
flow_app = typer.Typer(help="Manage and execute AI Flows")
app.add_typer(flow_app, name="flow")

@flow_app.command("create")
def flow_create(prompt: str):
    """Generate a new flow using the Magic Wand."""
    from core.flow_generator import magic_create_flow
    import json
    print(f"[bold blue]Magic Wand[/bold blue]: Generating flow for '{prompt}'...")
    try:
        flow_json = magic_create_flow(prompt)
        print("[green]Successfully generated flow![/green]")
        print(json.dumps(flow_json, indent=2))
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

@flow_app.command("list")
def flow_list():
    """List all saved flows."""
    from core.local_db import local_db
    from auth.supabase_client import get_current_user
    user = get_current_user()
    ws_id = local_db.get_or_create_workspace(user["id"] if user else "local_user")
    flows = local_db.get_flows_for_workspace(ws_id)
    if not flows:
        print("[yellow]No flows found in current workspace.[/yellow]")
        return
    print("[bold blue]Saved Flows:[/bold blue]")
    for f in flows:
        print(f"ID: [cyan]{f['id']}[/cyan] | Name: {f.get('name', 'Unnamed')}")

@flow_app.command("run")
def flow_run(flow_id: str):
    """Execute a built flow by its ID."""
    from core.orchestrator import run_flow
    from core.local_db import local_db
    flow = local_db.get_flow(flow_id)
    if not flow:
        print(f"[red]Flow {flow_id} not found.[/red]")
        return
    print(f"[bold blue]Running Flow:[/bold blue] {flow.get('name', 'Unnamed')}")
    try:
        results = run_flow(flow)
        print("[green]Flow execution successful![/green]")
        print(results)
    except Exception as e:
        print(f"[red]Error executing flow:[/red] {e}")

# --- Macro Commands ---
macro_app = typer.Typer(help="Record and manage self-healing macros")
app.add_typer(macro_app, name="macro")

@macro_app.command("start")
def macro_start():
    """Start recording a macro."""
    from core.macro_recorder import recorder
    try:
        msg = recorder.start_recording()
        print(f"[green]{msg}[/green]")
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

@macro_app.command("stop")
def macro_stop():
    """Stop the current macro recording."""
    from core.macro_recorder import recorder
    try:
        msg = recorder.stop_recording()
        print(f"[green]{msg}[/green]")
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

# --- Plugin Marketplace Commands ---
plugin_app = typer.Typer(help="Manage plugins from the marketplace")
app.add_typer(plugin_app, name="plugin")

@plugin_app.command("install")
def plugin_install(plugin_id: str):
    """Install a plugin from the marketplace."""
    from core.plugins.plugin_manager import plugin_manager
    try:
        success = plugin_manager.install_plugin(plugin_id)
        if success:
            print(f"[green]Successfully installed '{plugin_id}'.[/green]")
        else:
            print(f"[red]Failed to install '{plugin_id}'.[/red]")
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

@plugin_app.command("uninstall")
def plugin_uninstall(plugin_id: str):
    """Uninstall a local plugin."""
    from core.plugins.plugin_manager import plugin_manager
    try:
        success = plugin_manager.uninstall_plugin(plugin_id)
        if success:
            print(f"[green]Successfully uninstalled '{plugin_id}'.[/green]")
        else:
            print(f"[red]Failed to uninstall '{plugin_id}'.[/red]")
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

# --- Swarm Commands ---
swarm_app = typer.Typer(help="Orchestrate multi-agent swarms")
app.add_typer(swarm_app, name="swarm")

@swarm_app.command("run")
def swarm_run(task: str, manager_id: str, worker_ids: str):
    """Run a swarm orchestration. Workers should be comma-separated."""
    from core.swarm import swarm
    workers = [w.strip() for w in worker_ids.split(",") if w.strip()]
    if not workers:
        print("[red]Error: You must provide at least one worker ID.[/red]")
        return
    
    print(f"[bold blue]Initiating Swarm Orchestration:[/bold blue]")
    print(f"Task: {task}")
    print(f"Manager: {manager_id} | Workers: {workers}")
    try:
        result = swarm.run_swarm(task=task, manager_bot_id=manager_id, worker_bot_ids=workers, workspace_id="cli_user")
        print("[green]Swarm Task Complete![/green]\n")
        print("[bold]Synthesis Report:[/bold]")
        print(result.get("final_answer", ""))
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

# --- Phase 13: Activity, Webhooks, Memory ---
activity_app = typer.Typer(help="View real-time agent activity")
app.add_typer(activity_app, name="activity")

@activity_app.command("log")
def activity_log(limit: int = 20):
    """Show recent activity logs."""
    from core.activity_feed import activity_feed
    events = activity_feed.get_recent(limit)
    if not events:
        print("[yellow]No recent activity.[/yellow]")
        return
    for ev in events:
        print(f"[[blue]{ev['ts']}[/blue]] [bold]{ev['type'].upper()}[/bold] - {ev['detail']}")

hook_app = typer.Typer(help="Manage webhook triggers for flows")
app.add_typer(hook_app, name="hook")

@hook_app.command("list")
def hook_list():
    """List all configured webhooks."""
    from core.local_db import _get_connection
    conn = _get_connection()
    rows = conn.execute("SELECT id, flow_id, label FROM webhooks").fetchall()
    if not rows:
        print("[yellow]No webhooks found.[/yellow]")
        return
    for r in rows:
        print(f"ID: [green]{r['id']}[/green] | Flow: {r['flow_id']} | Label: {r['label']}")

@hook_app.command("trigger")
def hook_trigger(hook_id: str):
    """Manually trigger a webhook flow."""
    import requests
    try:
        resp = requests.post(f"http://localhost:8501/api/hooks/{hook_id}")
        print(f"[green]Triggered![/green] Status: {resp.status_code}")
        print(resp.json())
    except Exception as e:
        print(f"[red]Error:[/red] {e}")

memory_app = typer.Typer(help="Search chat memory")
app.add_typer(memory_app, name="memory")

@memory_app.command("search")
def memory_search(q: str):
    """Search all past chat histories for a keyword."""
    from core.local_db import _get_connection
    import json
    conn = _get_connection()
    rows = conn.execute("SELECT id, title, messages FROM chat_histories").fetchall()
    found = False
    for r in rows:
        msgs = json.loads(r["messages"]) if r["messages"] else []
        for m in msgs:
            if q.lower() in m.get("content", "").lower():
                print(f"\n[bold blue]Match in: {r['title']}[/bold blue] ({r['id']})")
                print(f"[dim]{m.get('role')}:[/dim] {m.get('content')[:150]}...")
                found = True
                break
    if not found:
        print("[yellow]No matches found.[/yellow]")

if __name__ == "__main__":
    app()
