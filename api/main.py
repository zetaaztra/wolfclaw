import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Initialize FastAPI App
app = FastAPI(title="Wolfclaw API", version="1.0.0")

# CORS (in case we need to talk to it from outside localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check ---
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# --- Include API Routers ---
from api.routes import auth, bots, settings, remote, chat, channels, account, tools, templates, favorites, documents, history, knowledge, analytics, scheduler, reports, flows, integrations, macros, marketplace, flow_templates

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(bots.router, prefix="/api/bots", tags=["Bot Management"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(remote.router, prefix="/api/remote", tags=["Remote Servers"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(channels.router, prefix="/api/channels", tags=["Channels"])
app.include_router(account.router, prefix="/api/account", tags=["Account Management"])
app.include_router(tools.router, prefix="/api/tools", tags=["Tools"])
app.include_router(templates.router, prefix="/api", tags=["Templates"])
app.include_router(favorites.router, prefix="/api", tags=["Favorites"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(knowledge.router, prefix="/api", tags=["Knowledge Base"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(scheduler.router, prefix="/api", tags=["Scheduler"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(flows.router, prefix="/api/flows", tags=["Flows"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(macros.router, prefix="/api/macros", tags=["Macros"])
app.include_router(marketplace.router, prefix="/api/marketplace", tags=["Marketplace"])
app.include_router(flow_templates.router, prefix="/api", tags=["Flow Templates"])

# --- Serve Frontend SPA ---
# Mount the static directory for CSS/JS assets
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Catch-all route to serve the Single Page Application (index.html)
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    # If the user is trying to access an API route that doesn't exist, let it 404
    if full_path.startswith("api/"):
        return {"error": "API route not found"}
        
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8501)
