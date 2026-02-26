"""
Flow Templates — Pre-built Flow JSON graphs that users can import with one click.
"""
from fastapi import APIRouter

router = APIRouter()

FLOW_TEMPLATES = [
    {
        "id": "daily_news",
        "name": "📰 Daily News Summarizer",
        "description": "Scrapes top news headlines every morning and sends a summary to your email.",
        "category": "Productivity",
        "flow_data": {
            "drawflow": {
                "Home": {
                    "data": {
                        "1": {
                            "id": 1, "name": "manual_trigger", "class": "manual_trigger",
                            "html": "Manual Trigger", "typenode": False,
                            "data": {"label": "Every Morning", "timezone": "UTC"},
                            "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                            "pos_x": 50, "pos_y": 100
                        },
                        "2": {
                            "id": 2, "name": "web_scrape", "class": "web_scrape",
                            "html": "Web Scrape", "typenode": False,
                            "data": {"label": "Scrape News", "url": "https://news.google.com", "selector": "article h3"},
                            "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                            "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                            "pos_x": 300, "pos_y": 100
                        },
                        "3": {
                            "id": 3, "name": "ai_summarize", "class": "ai_summarize",
                            "html": "AI Summarize", "typenode": False,
                            "data": {"label": "Summarize Headlines", "prompt": "Summarize these news headlines into a concise morning briefing:"},
                            "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                            "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}},
                            "pos_x": 550, "pos_y": 100
                        },
                        "4": {
                            "id": 4, "name": "send_email", "class": "send_email",
                            "html": "Send Email", "typenode": False,
                            "data": {"label": "Email Summary", "to": "", "subject": "Your Daily News Briefing"},
                            "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}},
                            "outputs": {},
                            "pos_x": 800, "pos_y": 100
                        }
                    }
                }
            }
        }
    },
    {
        "id": "vision_doc",
        "name": "👁️ Vision Document Analyzer",
        "description": "Upload a document screenshot, analyze it with GPT-4o Vision, and get a structured summary.",
        "category": "AI Tools",
        "flow_data": {
            "drawflow": {
                "Home": {
                    "data": {
                        "1": {
                            "id": 1, "name": "manual_trigger", "class": "manual_trigger",
                            "html": "Manual Trigger", "typenode": False,
                            "data": {"label": "Start Analysis"},
                            "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                            "pos_x": 50, "pos_y": 100
                        },
                        "2": {
                            "id": 2, "name": "ai_summarize", "class": "ai_summarize",
                            "html": "AI Vision", "typenode": False,
                            "data": {"label": "Analyze with GPT-4o", "prompt": "Analyze this document image and extract all key information into a structured format with headings, bullet points, and tables."},
                            "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                            "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                            "pos_x": 300, "pos_y": 100
                        },
                        "3": {
                            "id": 3, "name": "send_telegram", "class": "send_telegram",
                            "html": "Send Telegram", "typenode": False,
                            "data": {"label": "Send Result", "bot_token": "", "chat_id": ""},
                            "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                            "outputs": {},
                            "pos_x": 550, "pos_y": 100
                        }
                    }
                }
            }
        }
    },
    {
        "id": "slack_reporter",
        "name": "💬 Web Scrape → Slack Reporter",
        "description": "Scrape a website, summarize content with AI, and post results to a Slack channel.",
        "category": "Integrations",
        "flow_data": {
            "drawflow": {
                "Home": {
                    "data": {
                        "1": {
                            "id": 1, "name": "manual_trigger", "class": "manual_trigger",
                            "html": "Manual Trigger", "typenode": False,
                            "data": {"label": "Start Report"},
                            "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                            "pos_x": 50, "pos_y": 100
                        },
                        "2": {
                            "id": 2, "name": "web_scrape", "class": "web_scrape",
                            "html": "Web Scrape", "typenode": False,
                            "data": {"label": "Scrape Data", "url": "https://example.com", "selector": "main"},
                            "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                            "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                            "pos_x": 300, "pos_y": 100
                        },
                        "3": {
                            "id": 3, "name": "ai_summarize", "class": "ai_summarize",
                            "html": "AI Summarize", "typenode": False,
                            "data": {"label": "Analyze & Format", "prompt": "Analyze and format this data for a Slack report:"},
                            "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                            "outputs": {},
                            "pos_x": 550, "pos_y": 100
                        }
                    }
                }
            }
        }
    },
    {
        "id": "email_digest",
        "name": "📧 AI Email Digest",
        "description": "Trigger manually, run an AI prompt, and email the result — perfect for daily digests.",
        "category": "Productivity",
        "flow_data": {
            "drawflow": {
                "Home": {
                    "data": {
                        "1": {
                            "id": 1, "name": "manual_trigger", "class": "manual_trigger",
                            "html": "Manual Trigger", "typenode": False,
                            "data": {"label": "Morning Trigger", "timezone": "IST"},
                            "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                            "pos_x": 50, "pos_y": 100
                        },
                        "2": {
                            "id": 2, "name": "ai_summarize", "class": "ai_summarize",
                            "html": "AI Summarize", "typenode": False,
                            "data": {"label": "Generate Digest", "prompt": "Create a motivational morning digest with 3 productivity tips, a fun fact, and today's inspirational quote."},
                            "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                            "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                            "pos_x": 300, "pos_y": 100
                        },
                        "3": {
                            "id": 3, "name": "send_email", "class": "send_email",
                            "html": "Send Email", "typenode": False,
                            "data": {"label": "Send Digest", "to": "", "subject": "🌅 Your Morning AI Digest"},
                            "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                            "outputs": {},
                            "pos_x": 550, "pos_y": 100
                        }
                    }
                }
            }
        }
    }
]


@router.get("/flow-templates")
async def get_flow_templates():
    """Return list of available flow templates."""
    return {
        "templates": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "category": t["category"]
            }
            for t in FLOW_TEMPLATES
        ]
    }


@router.get("/flow-templates/{template_id}")
async def get_flow_template(template_id: str):
    """Return a specific flow template with its full flow_data."""
    for t in FLOW_TEMPLATES:
        if t["id"] == template_id:
            return t
    return {"error": "Template not found"}
