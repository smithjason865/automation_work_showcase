"""Utils for running tests"""

import os
import logging
import json
import time
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

_TEST_RESULTS_FILE_NAME = "test_results.txt"
_TEST_RESULTS_TEMPLATE = "test_results_template.txt"

class TestCaseResults:
    """Standard format for Test Results."""
    def __init__(
            self,
            test_case_name: str,
            test_case_id: str,
            test_description: str,
            assigned_tester: str,
            time_stamp: str,
            status: str
    ):
        self.test_case_name = 'Create a file with LLM'
        self.test_case_id: str = 'F1'
        self.test_description: str = 'Tests that a file can be created via LLM.'
        self.assigned_tester: str = 'John Doe'
        self.time_stamp: str = time.strftime("%Y_%m_%dT%H_%M_%S")
        self.status: str = 'untested'

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

def remove_file_from_current_dir(file:str) -> bool:
    """Removes a file from the current directory.
    Args:
        file (str): The file to remove.
    Returns:
        bool: True if the file was removed, False otherwise.
    """
    # Attempt to remove file
    logging.info(f"Removing file '{file}'...")
    current_dir = os.getcwd()
    if file in os.listdir(current_dir):
        os.remove(file)
    else:
        logging.info(f"File '{file}' not found. Will not attempt to remove file.")
        return True
    # Confirm file was removed
    if file in os.listdir(current_dir):
        logging.error(f"Error: File '{file}' was not removed.")
        return False
    logging.info(f"File '{file}' was removed.")
    return True

def post_test_results_to_file(test_results: List, test_suite: str) -> bool:
    """Post test results to a file.
    Args:
        test_results (List): A list containing test results.
        test_suite (str): The name of the test suite.
    Returns:
        bool: True if results file was created, False otherwise.
    """

    # Create test results file
    timestamp = time.strftime("%Y_%m_%dT%H_%M_%S")
    results_file = f"{timestamp}_{test_suite}_{_TEST_RESULTS_FILE_NAME}"
    passed = 0
    failed = 0
    for result in test_results:
        if "passed" in str(result):
            passed += 1
        if "failed" in str(result):
            failed += 1
    with open(results_file, "w") as file:
        file.write(
            f"Test Results for Test Suite: {test_suite}\n"
            "\n"
            "Overall Test Results:\n"
            f"Total Tests: {len(test_results)}\n"
            f"Passed: {passed}\n"
            f"Failed: {failed}\n"
            "\n"
            "Individual Test Results:\n"
        )
        for result in test_results:
            file.write("\n")
            for item in result:
                file.write(item)
                file.write("\n")

    # Confirm file exists
    current_dir = os.getcwd()
    if file in os.listdir(current_dir):
        logging.info(f"File '{results_file}' was successfully created.")
        return True
    logging.error(f"Error: File '{results_file}' was not created.")
    return False

def post_test_results_using_llm(test_results: List, test_suite: str) -> bool:
    """Use LLM to construct a test results file in Agile format.
    Args:
        test_results (List): A list containing test results.
        test_suite (str): The name of the test suite.
    Returns:
        bool: True if results file was created, False otherwise.
    """

    # Use LLM for OpenAI to create a results file (.xsls or Excel) which contains test results in Agile format
    timestamp = time.strftime("%Y_%m_%dT%H_%M_%S")
    results_file = f"{timestamp}_{test_suite}_{_TEST_RESULTS_FILE_NAME}"
    messages = [
        {"role": "system", "content": (
            "You are a QA manager for a major Tech company and follow the Agile process. You collect all test "
            "results. You always gather overall results and then list individual results with the following info: "
            "test case name, test case ID, test description, assigned tester, time stamp, and status. Refer to "
            f"'{_TEST_RESULTS_TEMPLATE}' as a template for how to store results."
        )
         },
        {"role": "user", "content": (
            f"Using the collected test results '{test_results}', create a results file named "
            f"'{results_file}' and store the results there with overall results printed at top and "
            "individual results below."
        )
         },
    ]
    returned_response = generate_local_response(messages)
    user_query = f"Using the collected test results '{test_results}', write to a results file named "\
                 f"'{results_file}' and store the results there with overall results printed at top and "\
                 f"individual results below. Refer to '{_TEST_RESULTS_TEMPLATE}' as a template for how to "\
                 "store results."
    if returned_response:
        # Use file management agent to create results file
        file_response = file_management_agent.file_management_request(user_input=user_query)
        if file_response:
            # Confirm test results file exists
            current_dir = os.getcwd()
            if results_file in os.listdir(current_dir):
                logging.info(f"File '{results_file}' was successfully created.")
                return True
            logging.error(f"Error: File '{results_file}' was not created.")
            return False
        logging.error(f"Error: Issue communicating with 'file management agent'.")
        return False
    logging.error(f"Error: Issue communicating with LLM to create results file '{results_file}'.")
    return False