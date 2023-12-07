"""Tests for the `utils.include_orphaned_processes` function."""

import unittest

import pandas as pd

from shinigami.utils import include_orphaned_processes, INIT_PROCESS_ID


class OrphanedProcesses(unittest.TestCase):
    """Test the identification of orphaned processes from a DataFrame of process data"""

    def test_orphaned_processes_are_returned(self) -> None:
        """Test orphaned processes are returned from a DataFrame of process data"""

        input_df = pd.DataFrame({
            'PID': [1, 2, 3, 4, 5],
            'PPID': [0, INIT_PROCESS_ID, INIT_PROCESS_ID, 2000, 2000],
            'PGID': [0, 0, 0, 0, 0],
            'UID': [0, 1, 1, 2, 2],
            'CMD': ['init', 'process_1', 'process_2', 'process_3', 'process_4']})

        # Manually define the data subset (including the index) expected in the function return
        expected_output_df = pd.DataFrame({
            'PID': [2, 3],
            'PPID': [INIT_PROCESS_ID, INIT_PROCESS_ID],
            'PGID': [0, 0],
            'UID': [1, 1],
            'CMD': ['process_1', 'process_2']},
            index=[1, 2])

        pd.testing.assert_frame_equal(
            include_orphaned_processes(input_df),
            expected_output_df)

    def test_no_orphaned_processes(self) -> None:
        """Test the returned DataFrame is empty when no orphaned processes are present"""

        input_df = pd.DataFrame({
            'PID': [1, 2, 3, 4, 5],
            'PPID': [0, 2, 3, 4, 4],
            'PGID': [0, 0, 0, 0, 0],
            'UID': [0, 1, 1, 2, 2],
            'CMD': ['init', 'process_1', 'process_2', 'process_3', 'process_4']})

        self.assertTrue(include_orphaned_processes(input_df).empty)

    def test_all_orphaned_processes(self) -> None:
        """Test the returned DataFrame matches the input DataFrame when all processes are orphaned"""

        input_df = pd.DataFrame({
            'PID': [2, 3, 4, 5],
            'PPID': [INIT_PROCESS_ID, INIT_PROCESS_ID, INIT_PROCESS_ID, INIT_PROCESS_ID],
            'PGID': [0, 0, 0, 0],
            'UID': [1, 1, 2, 2],
            'CMD': ['process_1', 'process_2', 'process_3', 'process_4']})

        returned_df = include_orphaned_processes(input_df)
        pd.testing.assert_frame_equal(returned_df, input_df)

        # Make sure the return value is an equivalent copy and not just the original DataFrame
        self.assertIsNot(returned_df, input_df)
