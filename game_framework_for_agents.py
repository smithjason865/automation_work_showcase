"""GAME FRAMEWORK for constructing agents to communicate with LLMs"""
import json
import time
import traceback
from litellm import completion
from typing import Any, Callable, List, Dict
from dataclasses import dataclass, field

@dataclass
class Prompt:
    messages: List[Dict] = field(default_factory=list)
    tools: List[Dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

def generate_response(prompt: Prompt) -> str:
    """Call LLM to get response"""
    messages = prompt.messages
    tools = prompt.tools

    if not tools:
        response = completion(
            model="openai/gpt-4o",
            messages=messages,
            max_tokens=1024

        )
        result = response.choices[0].message.content
    else:
        response = completion(
            model="openai/gpt-4o",
            messages=messages,
            tools=tools,
            max_tokens=1024

        )
        if response.choices[0].message.tool_calls:
            tool = response.choices[0].message.tool_calls[0]
            result = {
                "tool": tool.function.name,
                "args": json.loads(tool.function.arguments)
            }
            result = json.dumps(result)
        else:
            result = response.choices[0].message.content
    return result

# For assigning Goals to the agent rules or behavior
@dataclass(frozen=True)
class Goal:
    priority: int
    name: str
    description: str

class Action:
    def __init__(self,
                 name: str,
                 function: Callable,
                 description: str,
                 parameters: dict,
                 terminal: bool = False,
                 ):
        self.name = name
        self.function = function
        self.description = description
        self.parameters = parameters
        self.terminal = terminal
    def execute(self, **args) -> Any:
        """Execute the action's function"""
        return self.function(**args)

class ActionRegistry:
    def __init__(self):
        self.actions = {}
    def register(self, action: Action):
        self.actions[action.name] = action
    def get_action(self, name: str) -> Action:
        return self.actions.get(name, None)
    def get_actions(self) -> List[Action]:
        """Get all registered actions"""
        return list(self.actions.values())

class Memory:
    def __init__(self):
        self.items = []
    def add_memory(self, memory: dict[str, str]):
        """Add a memory to working memory"""
        self.items.append(memory)
    def get_memories(self, limit: int | None = None) -> List[dict[str, str]]:
        """Get formatted conversation history for prompt"""
        try:
            limit = len(self.items) if limit is None else limit
        except TypeError as e:
            raise AssertionError(f"Could not get limit for memory.Error: {e}")
        if limit:
            return self.items[:limit]
        else:
            raise AssertionError("Error: Memory is empty")
    def copy_without_system_memories(self):
        """Return a copy of memories without system memory"""
        filtered_items = [m for m in self.items if m["type"] != "system"]
        memory = Memory()
        memory.items = filtered_items
        return memory

class Environment:
    def execute_action(self, action: Action, args: dict) -> dict:
        """Execute an action and return the result"""
        try:
            result = action.execute(**args)
            return self.format_result(result)
        except Exception as e:
            return {
                "tool_executed": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
    @staticmethod
    def format_result(result: Any) -> dict:
        """Format the result with metadata"""
        return {
            "tool_executed": True,
            "result": result,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

class AgentLanguage:
    def __init__(self):
        pass

    def construct_prompt(
            self,
            actions: List[Action],
            environment: Environment,
            goals: List[Goal],
            memory: Memory,
    ) -> Prompt:
        raise NotImplementedError("Subclasses must implement this method")

    def parse_response(self, response: str) -> dict:
        raise NotImplementedError("Subclasses must implement this method")

class AgentFunctionCallingActionLanguage(AgentLanguage):
    def __init__(self):
        super().__init__()

    @staticmethod
    def format_goals(goals: List[Goal]) -> List:
        # Map all goals to a single string that concatenates their description
        # and combine into a single message of type system
        sep = "\n-------------------\n"
        goal_instructions = "\n\n".join([f"{goal.name}:{sep}{goal.description}{sep}" for goal in goals])
        return [
            {"role": "system", "content": goal_instructions}
        ]

    @staticmethod
    def format_memory(memory: Memory) -> List:
        # Map all environment results to a role:assistant messages
        # Map all assistant messages to role:assistant messages
        # Map all user messages to role:user messages
        items = memory.get_memories()
        mapped_items = []
        for item in items:
            content = item.get("content", None)
            if not content:
                content = json.dumps(item, indent=4)
            if item["type"] == "assistant":
                mapped_items.append({"role": "assistant", "content": content})
            elif item["type"] == "environment":
                mapped_items.append({"role": "assistant", "content": content})
            else:
                mapped_items.append({"role": "user", "content": content})
        return mapped_items

    @staticmethod
    def format_actions(actions: List[Action]) -> List:
        """Generate response from language model"""

        tools = [
            {
                "type": "function",
                "function": {
                    "name": action.name,
                    # Include up to 1024 characters of the description
                    "description": action.description[:1024],
                    "parameters": action.parameters,
                },
            } for action in actions
        ]
        return tools

    def construct_prompt(
            self,
            actions: List[Action],
            environment: Environment,
            goals: List[Goal],
            memory: Memory,
    ) -> Prompt:
        prompt = []
        prompt += self.format_goals(goals)
        prompt += self.format_memory(memory)

        tools = self.format_actions(actions)

        return Prompt(messages=prompt, tools=tools)

    @staticmethod
    def adapt_prompt_after_parsing_error(
            self,
            prompt: Prompt,
            response: str,
            traceback: str,
            error: Any,
            retries_left: int,
    ) -> Prompt:
        return prompt

    def parse_response(self, response: str) -> dict:
        """Parse LLM response into structured format by extracting the ```json block"""

        try:
            return json.loads(response)
        except json.decoder.JSONDecodeError:
            return {
                "tool": "terminate",
                "args": {"message":response},
            }


class Agent:
    def __init__(
            self,
            goals: list[Goal],
            agent_language: AgentLanguage,
            action_registry: ActionRegistry,
            generate_response: Callable[[Prompt], str],
            environment: Environment,
    ):
        """Initialize an agent with its core GAME components"""
        self.goals = goals
        self.agent_language = agent_language
        self.generate_response = generate_response
        self.environment = environment
        self.actions = action_registry

    def construct_prompt(
            self,
            goals: List[Goal],
            memory: Memory,
            actions: ActionRegistry,
    ) -> Prompt:
        """Build prompt with memory context"""
        return self.agent_language.construct_prompt(
            actions=actions.get_actions(),
            environment=self.environment,
            goals=goals,
            memory=memory,
        )

    def get_action(self, response):
        invocation = self.agent_language.parse_response(response)
        action = self.actions.get_action(invocation["tool"])
        if action == "terminate":
            action.terminal = True
        return action, invocation

    def should_terminate(self, response: str) -> bool:
        action_def, _ = self.get_action(response)
        # Implemented to handle 'NoneType' conditions
        if action_def.terminal:
            return action_def.terminal
        else:
            return True

    @staticmethod
    def set_current_task(memory: Memory, task: str):
        memory.add_memory({"type": "user", "content": task})

    @staticmethod
    def update_memory(memory: Memory, response: str, result: dict):
        """Update memory with the agent's decision and the environment's response"""
        new_memories = [
            {"type": "assistant", "content": response},
            {"type": "environment", "content": json.dumps(result)},
        ]
        for m in new_memories:
            memory.add_memory(m)

    def prompt_llm_for_action(self, full_prompt: Prompt) -> str:
        response = self.generate_response(full_prompt)
        return response

    def run(self, user_input: str, memory=None, max_iterations: int = 50) -> Memory:
        """Execute the GAME loop for this agent with a maximum iteration limit"""
        memory = memory or Memory()
        self.set_current_task(memory=memory, task=user_input)
        for _ in range(max_iterations):
            # Construct a prompt that includes the Goals, Actions, and the current Memory
            prompt = self.construct_prompt(goals=self.goals, memory=memory, actions=self.actions)

            print("Agent thinking...")
            # Generate a response from the agent
            response = self.prompt_llm_for_action(prompt)
            print(f"Agent decision: {response}")

            # Determine which action the agent wants to execute
            action, invocation = self.get_action(response)

            # Execute the action in the environment
            result = self.environment.execute_action(action, invocation["args"])
            print(f"Agent result: {result}")

            # Update the agent's memory with information about what happened
            self.update_memory(memory, response, result)

            # Check if the agent has decided to terminate
            if self.should_terminate(response):
                break

        return memory