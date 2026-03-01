"""
Phase 14 — Bot-to-Bot Handoff / Intent Router
Automatically routes user messages to the best-matching bot based on intent.
"""
import logging
from core.local_db import _get_connection, get_key_local
from auth.supabase_client import get_current_user

logger = logging.getLogger(__name__)

# Keyword-based routing rules
DEFAULT_RULES = {
    "code": ["code", "python", "javascript", "debug", "error", "function", "api", "git", "deploy", "docker", "sql", "react", "html", "css"],
    "writing": ["write", "essay", "blog", "article", "email", "letter", "story", "poem", "caption", "content"],
    "research": ["research", "analyze", "compare", "find", "search", "explain", "what is", "how does"],
    "legal": ["contract", "legal", "compliance", "gdpr", "lawsuit", "attorney", "clause", "liability"],
    "finance": ["budget", "tax", "investment", "stock", "crypto", "savings", "expense", "revenue"],
    "creative": ["story", "song", "lyrics", "rpg", "character", "world", "fantasy", "fiction"],
}


class BotRouter:
    """Routes messages to the best bot based on content analysis."""

    def __init__(self):
        self._custom_rules = {}

    def set_rule(self, bot_id: str, keywords: list):
        """Set custom routing keywords for a specific bot."""
        self._custom_rules[bot_id] = [k.lower() for k in keywords]

    def remove_rule(self, bot_id: str):
        if bot_id in self._custom_rules:
            del self._custom_rules[bot_id]

    def get_rules(self) -> dict:
        return self._custom_rules.copy()

    def route(self, message: str, available_bots: dict) -> str:
        """Determine which bot should handle this message.
        
        Args:
            message: The user's input message
            available_bots: Dict of {bot_id: bot_info_dict}
            
        Returns:
            bot_id of the best match, or first available bot if no match
        """
        msg_lower = message.lower()
        scores = {}

        # Score with custom rules first
        for bot_id, keywords in self._custom_rules.items():
            if bot_id in available_bots:
                score = sum(1 for kw in keywords if kw in msg_lower)
                if score > 0:
                    scores[bot_id] = score

        # Score with default category rules matched to bot names
        for bot_id, bot_info in available_bots.items():
            bot_name = bot_info.get("name", "").lower()
            bot_prompt = bot_info.get("prompt", "").lower()[:200]

            for category, keywords in DEFAULT_RULES.items():
                # Check if bot name/prompt matches category
                if category in bot_name or category in bot_prompt:
                    keyword_score = sum(1 for kw in keywords if kw in msg_lower)
                    if keyword_score > 0:
                        scores[bot_id] = scores.get(bot_id, 0) + keyword_score

        if scores:
            best_bot = max(scores, key=scores.get)
            logger.info(f"BotRouter: routed to {best_bot} (score: {scores[best_bot]})")
            return best_bot

        # Fallback: return the first bot
        return next(iter(available_bots))

# Singleton
bot_router = BotRouter()
