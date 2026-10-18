"""Ask Agent module"""

import os
import json
from litellm import completion
from typing import Dict, List
import file_management_agent

# Important!!!
#
# <---- Set your 'OPENAI_API_KEY' as a secret over there with the "key" icon
#
# For LiteLLM usage and OpenAI AI agent, execute 'pip install litellm' in terminal
# For Gemini AI agent, execute 'pip install -q -U google-genai' in terminal

load_api_key = json.load(open("./api_keys.json"))
_OPENAI_API_KEY = load_api_key["openai_api_key"]

os.environ['OPENAI_API_KEY'] = _OPENAI_API_KEY

agents_dict: Dict[str,str] = {} # Needed for storing all read content for agent files

# This is needed to determine which agent to use
def generate_local_response(all_messages: List[Dict]) -> str | None:
    """Call LLM to get response"""
    response = completion(
        model="openai/gpt-4o",
        messages=all_messages,
        max_tokens=1024
    )
    result = response.choices[0].message.content
    if result is None:
        print("Error: No response returned from OpenAI API")
        return None
    else:
        return result

def identify_agents(user_input: str) -> str:
    """Identifies agents available for usage."""
    try:
        current_directory = os.getcwd()
        files = os.listdir(current_directory)
        for file_name in files:
            if file_name.endswith("_agent.py"):
                result_string = ""
                start_flag = True
                with open(file_name, "r") as file:
                    file.seek(0)
                    lines = file.readlines()
                    for line in lines:
                        if start_flag:
                            result_string = line
                            start_flag = False
                        else:
                            result_string += line
                agents_dict.update({file_name: result_string})
    except Exception as e:
        raise AssertionError(f"Failed to fetch agent results. Error: {e}")
    # Determine the agent to use from agents_dict
    messages = [
        {"role": "system", "content": (
            "You are an expert in determining which agent would be best to use for a user query based on the query "
            "and tools available for the agent. Possible agents with content are stored in python dictionary "
            f"format as '{agents_dict}' where file names are stored as keys. Only list the file name for the "
            "best agent to use excluding the '.py' extension as the key"
        )
            },
        {"role": "user", "content": (
            f"Using the following user query '{user_input}', which agent would be best to use?"
        )
         },
    ]
    returned_response = generate_local_response(messages)
    if returned_response:
        if f"{returned_response}.py" in agents_dict.keys():
            print(f"Identified best agent as: {returned_response}")

            # For debugging purposes, list the tools for the chosen agent
            tools_message = [
                {"role": "assistant", "content": messages[0]["content"]},
                {"role": "user", "content": (
                    f"List the tools associated with the agent '{returned_response}'"
                )
                 },
            ]
            tools_response = generate_local_response(tools_message)
            print(f"Available tools for '{returned_response}': {tools_response}")

            return returned_response
    raise AssertionError(f"Error: No agents available for usage.")

def main(user_input: str | None = None) -> str:
    """Main function"""
    # Perform a task
    if user_input is None:
        user_query = input("What would you like to ask?\n\n")
    else:
        user_query = user_input

    # Determine which agent to use
    agent_to_use = identify_agents(user_input=user_query)

    # Select agent operation
    if "file_management_agent" in agent_to_use:
        returned_result = file_management_agent.file_management_request(user_input=user_query)
        return str(returned_result)
    else:
        raise AssertionError(f"Error: Could not select agent path to use.")


if __name__ == "__main__":
    main()