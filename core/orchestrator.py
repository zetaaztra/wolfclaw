import json
import logging
from typing import List, Dict, Any
from core.llm_engine import WolfEngine
from core.bot_manager import get_bots

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """
    Handles 'War Room' multi-agent conversations.
    A Manager bot receives the user prompt, analyzes it, and delegates
    sub-tasks to a list of available specialized bots.
    """
    def __init__(self, manager_bot_id: str, sub_bot_ids: List[str]):
        self.manager_bot_id = manager_bot_id
        self.sub_bot_ids = sub_bot_ids
        
        # Load bot profiles once
        all_bots = get_bots()
        self.manager_bot = all_bots.get(manager_bot_id)
        self.sub_bots = {bid: all_bots.get(bid) for bid in sub_bot_ids if bid in all_bots}
        
        if not self.manager_bot:
            raise ValueError(f"Manager bot {manager_bot_id} not found.")
        if not self.sub_bots:
            raise ValueError("No valid sub-bots provided.")

    def run_war_room(self, user_prompt: str, chat_history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Executes the multi-agent orchestration sequence:
        1. Manager breaks down the task.
        2. Manager delegates to sub-bots.
        3. Sub-bots execute and return results.
        4. Manager synthesizes the final response.
        
        Returns a list of 'event' dicts that can be displayed in the UI sequentially.
        """
        events = []
        
        # 1. Provide Context to Manager
        sub_bots_info = "\n".join([
            f"- {bot_info['name']} (ID: {bot_id}): {bot_info['prompt'][:100]}..." 
            for bot_id, bot_info in self.sub_bots.items()
        ])
        
        orchestration_prompt = f"""
You are the Lead Manager of this War Room. You must accomplish the following user request:
"{user_prompt}"

You have the following specialized agents available to you:
{sub_bots_info}

Step 1: Break down the user's request into specific tasks.
Step 2: Assign EACH task to the most appropriate agent by referencing their exact ID.
Step 3: Output your plan as a valid JSON array of objects. NO OTHER TEXT. 
Format:
[
  {{
    "agent_id": "the-id-of-the-agent",
    "task": "The specific instruction for this agent"
  }}
]
"""
        
        events.append({
            "type": "status",
            "bot_name": self.manager_bot["name"],
            "content": "Analyzing task and delegating..."
        })
        
        # Initialize Manager Engine
        manager_engine = WolfEngine(self.manager_bot["model"], fallback_models=self.manager_bot.get("fallback_models", []))
        
        # Get Delegation Plan
        try:
            # We use a temporary history for the manager's meta-cognition
            temp_history = chat_history.copy()
            temp_history.append({"role": "user", "content": orchestration_prompt})
            
            response = manager_engine.chat(
                messages=temp_history,
                system_prompt="You are an expert project manager. You ONLY output valid JSON arrays.",
                bot_id=self.manager_bot_id
            )
            
            plan_text = response.choices[0].message.content
            
            # Extract JSON if markdown wrapped
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0].strip()
                
            delegation_plan = json.loads(plan_text)
            
        except Exception as e:
            logger.error(f"Failed to generate delegation plan: {e}")
            events.append({
                "type": "error",
                "bot_name": "System",
                "content": f"Manager failed to create a valid plan: {e}"
            })
            return events

        # 2. Execute Plan
        sub_results = []
        for task_item in delegation_plan:
            target_agent_id = task_item.get("agent_id")
            task_instruction = task_item.get("task")
            
            agent_profile = self.sub_bots.get(target_agent_id)
            if not agent_profile:
                continue
                
            events.append({
                "type": "status",
                "bot_name": agent_profile["name"],
                "content": f"Working on: {task_instruction}"
            })
            
            try:
                # Initialize Sub-Agent Engine
                agent_engine = WolfEngine(agent_profile["model"], fallback_models=agent_profile.get("fallback_models", []))
                
                # Contextualize the sub-agent's prompt
                agent_context = chat_history.copy()
                agent_context.append({
                    "role": "user", 
                    "content": f"The Manager has assigned you the following task:\n\n{task_instruction}\n\nPlease execute it."
                })
                
                res = agent_engine.chat(
                    messages=agent_context,
                    system_prompt=agent_profile["prompt"],
                    bot_id=target_agent_id
                )
                
                agent_reply = res.choices[0].message.content
                
                events.append({
                    "type": "message",
                    "bot_name": agent_profile["name"],
                    "content": agent_reply
                })
                
                sub_results.append({
                    "agent": agent_profile["name"],
                    "task": task_instruction,
                    "result": agent_reply
                })
                
            except Exception as e:
                events.append({
                    "type": "error",
                    "bot_name": agent_profile["name"],
                    "content": f"Failed to execute task: {e}"
                })

        # 3. Manager Synthesis
        events.append({
            "type": "status",
            "bot_name": self.manager_bot["name"],
            "content": "Synthesizing final response..."
        })
        
        synthesis_prompt = f"""
The sub-agents have completed their tasks. Here are their results:

{json.dumps(sub_results, indent=2)}

Please synthesize these results into a final, cohesive response for the user, answering their original request:
"{user_prompt}"
"""
        try:
            temp_history = chat_history.copy()
            temp_history.append({"role": "user", "content": synthesis_prompt})
            
            final_response = manager_engine.chat(
                messages=temp_history,
                system_prompt=self.manager_bot["prompt"],
                bot_id=self.manager_bot_id
            )
            
            final_reply = final_response.choices[0].message.content
            events.append({
                "type": "message",
                "bot_name": self.manager_bot["name"],
                "content": final_reply
            })
            
        except Exception as e:
            events.append({
                "type": "error",
                "bot_name": "System",
                "content": f"Manager synthesis failed: {e}"
            })

        return events
