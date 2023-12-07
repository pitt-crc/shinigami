"""Tests for the `utils.exclude_active_slurm_users` function"""

import unittest

import pandas as pd

from shinigami.utils import exclude_active_slurm_users


class ExcludeSlurmUsers(unittest.TestCase):
    """Test the identification of slurm users from a DataFrame of process data"""

    def test_exclude_slurm_users(self) -> None:
        """Test slurm processes are excluded from the returned DataFrame"""

        # User 1002 has two processes.
        # They BOTH should be excluded because ONE of them is a slurm process.
        input_df = pd.DataFrame({
            'UID': [1001, 1002, 1002, 1003, 1004],
            'CMD': ['process 1', 'slurmd ...', 'process 3', 'process 4', 'process5']})

        expected_df = input_df.loc[[0, 3, 4]]
        returned_df = exclude_active_slurm_users(input_df)
        pd.testing.assert_frame_equal(returned_df, expected_df)

    def test_no_slurm_users(self) -> None:
        """Test the returned dataframe matches the input dataframe when there are no slurm processes"""

        input_df = pd.DataFrame({
            'UID': [1001, 1002, 1003, 1004, 1005],
            'CMD': ['process1', 'process2', 'process3', 'process4', 'process5']})

        returned_df = exclude_active_slurm_users(input_df)
        pd.testing.assert_frame_equal(returned_df, input_df)

    def test_all_slurm_users(self) -> None:
        """Test the returned dataframe is empty when all process container `slurmd`"""

        input_df = pd.DataFrame({
            'UID': [1001, 1002, 1003],
            'CMD': ['slurmd', 'prefix slurmd', 'slurmd postfix']})

        returned_df = exclude_active_slurm_users(input_df)
        self.assertTrue(returned_df.empty)
