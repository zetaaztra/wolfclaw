import json
import logging
from typing import Dict, Any, List
from .llm_engine import WolfEngine
from .flow_engine import BLOCK_CATALOG

logger = logging.getLogger(__name__)

class FlowGenerator:
    """
    The 'Magic Wand' Engine. 
    Converts natural language prompts into executable Wolfclaw Flow JSON.
    """

    def __init__(self, model_name: str = "gpt-4o"):
        self.engine = WolfEngine(model_name)
        # Flatten catalog for the LLM
        self.block_schema = [
            {"type": b["type"], "label": b["label"], "category": b["category"]} 
            for b in BLOCK_CATALOG
        ]

    def generate_flow(self, user_prompt: str) -> Dict[str, Any]:
        """
        Takes a user's goal and returns a valid Flow JSON.
        """
        system_instruction = (
            "You are the Wolfclaw Flow Architect. Your job is to convert a user's automation goal into a valid JSON Flow.\n\n"
            "### BLOCK CATALOG (Only use these types):\n"
            f"{json.dumps(self.block_schema, indent=2)}\n\n"
            "### JSON FORMAT:\n"
            "{\n"
            "  \"nodes\": {\n"
            "    \"node_1\": {\"type\": \"manual_trigger\", \"config\": {}, \"position\": {\"x\": 100, \"y\": 100}},\n"
            "    \"node_2\": {\"type\": \"ai_prompt\", \"config\": {\"prompt\": \"...\"}, \"position\": {\"x\": 350, \"y\": 100}}\n"
            "  },\n"
            "  \"edges\": [\n"
            "    {\"from\": \"node_1\", \"to\": \"node_2\"}\n"
            "  ]\n"
            "}\n\n"
            "### RULES:\n"
            "1. ALWAYS start with a 'manual_trigger' unless a 'schedule_trigger' is implied.\n"
            "2. Use 'ai_prompt' for reasoning or summarization.\n"
            "3. Use 'terminal_command' for file operations or system tasks.\n"
            "4. Ensure node IDs are unique (node_1, node_2, etc.).\n"
            "5. The Flow must be a valid Directed Acyclic Graph (DAG).\n"
            "6. Output ONLY the raw JSON object. No markdown, no chatter."
        )

        messages = [{"role": "user", "content": f"Goal: {user_prompt}"}]
        
        try:
            # We use the raw chat method to ensure we get the JSON back
            kwargs = self.engine._build_completion_kwargs(self.engine.model_name, messages)
            kwargs["messages"].insert(0, {"role": "system", "content": system_instruction})
            kwargs.pop("tools", None) # No tools needed for generation itself
            
            from litellm import completion
            response = completion(**kwargs)
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from potential markdown markers
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "{" in content:
                content = content[content.find("{"):content.rfind("}")+1]
            
            flow_json = json.loads(content)
            return flow_json
            
        except Exception as e:
            logger.error(f"Flow generation failed: {e}")
            # Fallback to a simple manual trigger node
            return {
                "nodes": {"root": {"type": "manual_trigger", "config": {}, "position": {"x": 100, "y": 100}}},
                "edges": []
            }

def magic_create_flow(prompt: str) -> Dict[str, Any]:
    """Convenience helper for UI/CLI integration."""
    gen = FlowGenerator()
    return gen.generate_flow(prompt)
