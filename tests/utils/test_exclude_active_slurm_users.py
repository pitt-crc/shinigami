"""Tests for the `utils.exclude_active_slurm_users` function"""

import unittest

import pandas as pd

from shinigami.utils import exclude_active_slurm_users


class ExcludeSlurmUsers(unittest.TestCase):
    """Test the identification of slurm users from a DataFrame of process data"""

    def test_exclude_slurm_users(self) -> None:
        input_df = pd.DataFrame({
            'UID': [1001, 1002, 1003, 1004, 1005],
            'CMD': ['process_1', 'slurmd', 'process_3', 'process_4', 'process_5']})

        expected_df = input_df.loc[[0, 2, 3, 4]]
        returned_df = exclude_active_slurm_users(input_df)

        pd.testing.assert_frame_equal(returned_df, expected_df)
        self.assertIsNot(returned_df, input_df)

    def test_no_slurm_users(self) -> None:
        input_df = pd.DataFrame({
            'UID': [1001, 1002, 1003, 1004, 1005],
            'CMD': ['process_1', 'process_2', 'process_3', 'process_4', 'process_5']})

        returned_df = exclude_active_slurm_users(input_df)

        pd.testing.assert_frame_equal(returned_df, input_df)
        self.assertIsNot(returned_df, input_df)

    def test_all_slurm_users(self) -> None:
        input_df = pd.DataFrame({
            'UID': [1001, 1002, 1003, 1004, 1005],
            'CMD': ['slurmd', 'slurmd', 'slurmd', 'slurmd', 'slurmd']})

        returned_df = exclude_active_slurm_users(input_df)
        self.assertTrue(returned_df.empty)
        self.assertIsNot(returned_df, input_df)
