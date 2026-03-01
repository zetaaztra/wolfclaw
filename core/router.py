import json
import logging
from typing import Optional, Dict
from .llm_engine import WolfEngine

logger = logging.getLogger(__name__)

INTENT_CLASSES = {
    "coding": "Writing scripts, debugging code, or software architecture questions.",
    "research": "Finding facts, summarizing web info, or deep analysis of a topic.",
    "system_control": "Managing files, running power shell commands, or desktop automation.",
    "general_chat": "Casual conversation, jokes, or non-technical questions."
}

class SemanticRouter:
    """
    Intelligent router that determines the intent of a user query 
    to choose the best specialized bot/engine.
    """
    
    def __init__(self, routing_model: str = "gpt-4o-mini"):
        # We use a fast, cheap model for routing by default
        self.engine = WolfEngine(routing_model)

    def route_query(self, query: str) -> Dict[str, str]:
        """
        Classifies the query and returns a dict with 'intent' and 'reasoning'.
        """
        prompt = [
            {"role": "system", "content": 
                "You are the Wolfclaw Semantic Router. Classify the user query into one of the following classes:\n" +
                "\n".join([f"- {k}: {v}" for k, v in INTENT_CLASSES.items()]) +
                "\nOutput ONLY a JSON object: {\"intent\": \"class_name\", \"reasoning\": \"brief explanation\"}"
            },
            {"role": "user", "content": query}
        ]
        
        try:
            # We bypass the tool loop and ledger for the routing call itself
            # using a slimmed down kwargs set to avoid circular dependencies
            kwargs = self.engine._build_completion_kwargs(self.engine.model_name, prompt)
            kwargs.pop("tools", None)
            
            from litellm import completion
            response = completion(**kwargs)
            content = response.choices[0].message.content
            
            # Extract JSON from potential markdown blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
                
            return json.loads(content)
        except Exception as e:
            logger.warning(f"Semantic routing failed: {e}")
            return {"intent": "general_chat", "reasoning": "fallback due to error"}

def get_router():
    """Singleton-like access to the Semantic Router."""
    return SemanticRouter()
