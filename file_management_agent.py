"""File Management Agent"""

"""
This agent handles File Management conversations.
The following is defined here:
1. All tools needed for file management to be used by the agent
2. Agent rules and goal for behavior of agent when managing files
3. Any conversations that request file management
"""

import os
from game_framework_for_agents import *
from litellm import completion
from typing import Dict, List

# Important!!!
#
# <---- Set your 'OPENAI_API_KEY' as a secret over there with the "key" icon
#
# For LiteLLM usage and OpenAI AI agent, execute 'pip install litellm' in terminal
# For Gemini AI agent, execute 'pip install -q -U google-genai' in terminal

load_api_key = json.load(open("./api_keys.json"))
_OPENAI_API_KEY = load_api_key["openai_api_key"]

os.environ['OPENAI_API_KEY'] = _OPENAI_API_KEY

reading_dict: Dict[str,str] = {} # Needed for storing all read content

# This is needed to identify steps for determining when to terminate conversation
def generate_local_response(all_messages: List[Dict]) -> str | None:
    """Call LLM to get response"""
    response = completion(
        model="openai/gpt-4o",
        messages=all_messages,
        max_tokens=1024
    )
    result = response.choices[0].message.content
    if result is None:
        return "Error: No response returned from OpenAI API"
    else:
        return result

def file_management_request( user_input: str) -> List[dict[str, str]] | None:
    """File management agent construction"""

    # Determine instruction flow for determining when to terminate loop
    # Note: Add all major tool options here for simple steps
    messages = [
        {"role": "system", "content": (
            "You are a file manager. You can only list simple steps in numbered order and separate lines "
            "with the following choices used with given file names where relevant: 'list', 'create', 'delete', "
            "'write', 'read', 'document_in_python', and 'remaining'. If comparing files, make sure to have steps "
            "for reading each file prior to comparing. If list, assign each file name obtained to a "
            "read step if read is requested. 'remaining' is any additional step not covered by the other steps "
            "and you can print the full remaining step with 'remaining:' mentioned before rest of message. You "
            "can print in step relevant file names as needed for each step. For 'remaining' step use tool 'remaining'."
        )
         },
        {"role": "user", "content": f"List the steps for the following: {user_input}"},
    ]
    returned_response = generate_local_response(messages)
    print(returned_response)
    if returned_response:
        steps = returned_response.split("\n")
        print(steps) # DEBUG statement
    else:
        raise AssertionError("Error: No steps could be determined from user query.")

    # DEFINE THE AGENT'S GOALS HERE
    goals = [
        Goal(priority=1, name="Follow the steps", description=(
            f"Follow all the steps listed here: {steps}"
        )
             ),
        Goal(priority=1, name="Terminate", description=(
            f"Call the Terminate call when all steps '{steps}' have been completed and provide the result "
            "in the Terminate message"
        )
             ),
    ]

    # DEFINE THE AGENT'S LANGUAGE
    agent_language = AgentFunctionCallingActionLanguage()

    # DEFINE TOOLS FOR FILE MANAGEMENT AND REGISTER ACTIONS HERE
    action_registry = ActionRegistry()

    # 1) Listing files
    def list_files(extension: str | None = None) -> List[str]:
        """List all files with given extension in the current directory."""
        current_directory = os.getcwd()
        files = os.listdir(current_directory)
        if not extension:
            return files
        found_files = []
        for file_name in files:
            if file_name.endswith(f".{extension}"):
                found_files.append(file_name)
        return found_files

    action_registry.register(Action(
        name="list_files",
        function=list_files,
        description=(
            "List all files in the current directory that has the given extension. "
            "If no extension is given, all files are listed."
        ),
        parameters={
            "type": "object",
            "properties": {
                "extension": {
                    "type": "string",
                    "description": "The extension of the files to list. "
                }
            },
            "required": ["extension"]
        },
        terminal=False,
    ))

    # 2) Reading files
    def read_file(file_name: str) -> str:
        """Reads the content of a file."""
        try:
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
            reading_dict.update({file_name: result_string})
            return result_string
        except FileNotFoundError:
            return f"Error: File '{file_name}' not found."
        except Exception as e:
            return f"Could not read file '{file_name}'. Error: {str(e)}"

    # Populate the Action Registry
    action_registry.register(Action(
        name="read_file",
        function=read_file,
        description="Read the content of a file.",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "The name of the file to read."
                }
            },
            "required": ["file_name"]
        },
        terminal=False,
    ))

    # 3) Write contents to file
    def write_to_file(file_name: str, content: str) -> str:
        """Writes the content to a file."""
        try:
            with open(file_name, "a") as file:
                file.write("\n" + content)
            return f"Wrote content '{content}' to '{file_name}'."
        except FileNotFoundError:
            return f"Error: File '{file_name}' not found."
        except Exception as e:
            return f"Could not write to file '{file_name}'. Error: {str(e)}"

    # Populate the Action Registry
    action_registry.register(Action(
        name="write_to_file",
        function=write_to_file,
        description="Write content to a file.",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "The name of the file to write to."
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file."
                }
            },
            "required": ["file_name", "content"]
        },
        terminal=False,
    ))

    # 4) Delete file from directory
    def delete_file(file_name: str) -> str:
        """Deletes a file."""
        try:
            os.remove(file_name)
            return f"Deleted file '{file_name}'."
        except FileNotFoundError:
            return f"Error: File '{file_name}' not found."
        except Exception as e:
            return f"Could not delete file '{file_name}'. Error: {str(e)}"

    # Populate the Action Registry
    action_registry.register(Action(
        name="delete_file",
        function=delete_file,
        description="Delete a file from current directory.",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "The name of the file to delete."
                }
            },
            "required": ["file_name"]
        },
        terminal=False,
    ))

    # 5) Create file
    def create_file(file_name: str) -> str:
        """Creates a new file."""
        try:
            open(file_name, "w").close()
            return f"Created file '{file_name}'."
        except Exception as e:
            return f"Could not create a new file '{file_name}'. Error: {str(e)}"

    # Populate the Action Registry
    action_registry.register(Action(
        name="create_file",
        function=create_file,
        description="Create a new file.",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "The name of the file to create."
                }
            },
            "required": ["file_name"]
        },
        terminal=False,
    ))

    # 6) Add documentation to Python files
    def document_python_file(file_name: str) -> str:
        """Adds documentation to a Python file."""
        if ".py" not in file_name:
            return f"Error: File '{file_name}' is not a Python file."
        else:
            return f"Add documentation to '{file_name}'."

    # Populate the Action Registry
    action_registry.register(Action(
        name="document_python_file",
        function=document_python_file,
        description="Add documentation to a Python file.",
        parameters={
            "type": "object",
            "properties": {
                "file_name": {
                    "type": "string",
                    "description": "The name of the file to add documentation."
                }
            },
            "required": ["file_name"]
        },
        terminal=False,
    ))

    # 7) Perform remaining action
    def remaining(perform_remaining_step: str, fetched_memory: List[Dict[str,str]]) -> str:
        """Performs remaining action."""
        try:
            system = {"role": "system", "content": (
                "You can return normal results. Just return the result of the remaining action. "
                f"If needed, current files and content are in dictionary '{reading_dict}'"
            )
                      }
            message = {"role": "user", "content": f"{perform_remaining_step}."}
            print(f"Agent decision: {message}")
            fetched_memory.append(system)
            fetched_memory.append(message)
            full_message = fetched_memory
            response = generate_local_response(full_message)
            if response:
                return response
            return f"Error: Could not perform remaining action '{perform_remaining_step}'."
        except Exception as e:
            return f"Failed to perform remaining action '{perform_remaining_step}'. Error: {str(e)}"

    # Populate the Action Registry
    action_registry.register(Action(
        name="remaining",
        function=remaining,
        description="Perform remaining action.",
        parameters={
            "type": "object",
            "properties": {
                "perform_remaining_step": {
                    "type": "string",
                    "description": "A string of the remaining step to be performed."
                }
            },
            "required": ["perform_remaining_step"]
        },
        terminal=False,
    ))

    # DEFINE AGENT RULES / Goals

    file_management_goal = Goal(
        priority=1,
        name="file_management",
        description="""Manage files in the current directory by doing the following:
        1. Listing files when needed
        2. Reading file contents when needed
        3. Searching within files when information is required
        4. Providing helpful information about file contents
        5. Removing files when needed
        6. Creating files when needed
        7. Writing content to files when needed
        8. Performing remaining actions when needed
        """
    )

    # DEFINE THE ENVIRONMENT
    environment = Environment()

    # Perform the extracted steps from the user input
    final_memory = None
    for step in steps:
        print(step) # DEBUG statement
        if ("remaining:" not in step) and ("Remaining:" not in step):
            # CREATE AN AGENT INSTANCE
            agent = Agent(
                goals=goals,
                agent_language=agent_language,
                action_registry=action_registry,
                generate_response=generate_response,
                environment=environment
            )
            # RUN THE AGENT WITH USER INPUT
            final_memory = agent.run(user_input=step)
        else:
            if final_memory.get_memories():
                try:
                    print("Agent thinking for remaining action...")
                    result = remaining(perform_remaining_step=step, fetched_memory=final_memory.get_memories())
                    final_memory.add_memory({"type": "user", "content": step})
                    final_memory.add_memory({"type": "environment", "content": result})
                    full_result = '{"type": "environment", "content": ' + result + '}'
                    print(f"Agent result: {full_result}")
                except Exception as e:
                    raise AssertionError(f"Failed to perform remaining step '{step}'. Error: {str(e)}")
            else:
                raise AssertionError(f"Could not fetch memory to perform remaining step '{step}'.")

    # PRINT THE FINAL MEMORY AND RETURN IT
    if final_memory:
        print(final_memory.get_memories())
        return final_memory.get_memories()
    raise AssertionError("Error: LLM agent for File Management could not process steps.")
