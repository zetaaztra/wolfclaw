import json
import logging
from typing import List, Dict
from .llm_engine import WolfEngine

logger = logging.getLogger(__name__)

class GoalPlanner:
    """
    Decomposes a high-level goal into a structured task list 
    for autonomous execution.
    """
    
    def __init__(self, planning_model: str = "gpt-4o"):
        self.engine = WolfEngine(planning_model)

    def generate_plan(self, goal: str) -> List[Dict]:
        """
        Takes a goal string and returns a list of sub-tasks.
        Each task: {"id": 1, "task": "...", "status": "pending", "dependencies": []}
        """
        prompt = [
            {"role": "system", "content": 
                "You are the Wolfclaw Goal Decomposition Engine. Break the user's goal into a realistic sequence of small executive tasks. "
                "Each task must be something an AI agent can do (e.g., 'Run a command', 'Write a file', 'Search the web'). "
                "Output ONLY a JSON list of tasks: [{\"id\": 1, \"task\": \"title\", \"description\": \"...\", \"dependencies\": []}]"
            },
            {"role": "user", "content": f"Goal: {goal}"}
        ]
        
        try:
            kwargs = self.engine._build_completion_kwargs(self.engine.model_name, prompt)
            kwargs.pop("tools", None)
            
            from litellm import completion
            response = completion(**kwargs)
            content = response.choices[0].message.content
            
            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "[" in content:
                content = content[content.find("["):content.rfind("]")+1]
                
            tasks = json.loads(content)
            # Ensure each task has a status
            for t in tasks:
                t["status"] = "pending"
            return tasks
        except Exception as e:
            logger.error(f"Goal planning failed: {e}")
            return [{"id": 1, "task": "Direct Execution", "description": goal, "status": "pending", "dependencies": []}]

def get_planner():
    return GoalPlanner()
