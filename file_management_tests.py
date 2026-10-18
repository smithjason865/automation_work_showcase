import os

import logging
import time
from mobly import base_test
from mobly import test_runner
from mobly import asserts
import ask_agent_main
import testing_utils

_TEST_FILE = 'TempFile.txt'


class FileManagementTestsUsingLLM(base_test.BaseTestClass):
    """An assortment of File Management Tests using default OpenAI LLM."""
    test_results = [] # Store test results here

    def create_results_list(self, test_results: testing_utils.TestCaseResults):
        """Creates results list for test results."""
        results_list = [
            f'test case name: {test_results.test_case_name}',
            f'test case id: {test_results.test_case_id}',
            f'assigned tester: {test_results.assigned_tester}',
            f'test description: {test_results.test_description}',
            f'timestamp: {test_results.time_stamp}',
            f'status: {test_results.status}',
        ]
        return results_list


    def setup_class(self):
        print("Setting up file_management_tests...")
        asserts.assert_true(
            testing_utils.remove_file_from_current_dir(file=_TEST_FILE),
            f'Error: {_TEST_FILE} not removed from current directory.'
        )

    def teardown_class(self):
        print("Tearing down file_management_tests...")
        asserts.assert_true(
            testing_utils.remove_file_from_current_dir(file=_TEST_FILE),
            f'Error: {_TEST_FILE} not removed from current directory.'
        )
        logging.info('Posting file_management_test results...')
        testing_utils.post_test_results_to_file(
            test_results=self.test_results,
            test_suite='File Management Tests Using LLM'
        )

    def test_create_a_file_with_llm(self,
                                    test_create_a_file_with_llm_results = (
                                            testing_utils.TestCaseResults(
                                                test_case_name='Create a file with LLM',
                                                test_case_id='F1',
                                                assigned_tester='John Doe',
                                                test_description='Tests that a file can be created via LLM.',
                                                time_stamp=time.strftime("%Y_%m_%dT%H_%M_%S"),
                                                status='untested'
                                            )
                                    )
                                    ):
        """Tests that a file can be created via LLM."""

        result = ask_agent_main.main(f'Can you create file "{_TEST_FILE}"?')
        print(result)
        current_directory = os.getcwd()
        if _TEST_FILE not in os.listdir(current_directory):
            # Update test formatted results
            test_create_a_file_with_llm_results.status = 'failed'
            self.test_results.append(
                self.create_results_list(
                    test_create_a_file_with_llm_results
                )
            )
            asserts.fail(f'Error: {_TEST_FILE} not found in current directory')

        logging.info(f'Created file "{_TEST_FILE}".')

        # Update test formatted results
        test_create_a_file_with_llm_results.status = 'passed'
        self.test_results.append(
            self.create_results_list(
                test_results=test_create_a_file_with_llm_results
            )
        )

        logging.info('Test Passed')

if __name__ == '__main__':
  test_runner.main()