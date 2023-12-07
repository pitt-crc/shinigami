"""Tests for the `include_user_whitelist` function."""

from unittest import TestCase

import pandas as pd

from shinigami.utils import INIT_PROCESS_ID, include_user_whitelist


class WhitelistedIDs(TestCase):
    """Tests for the ``id_in_whitelist`` function"""

    def setUp(self) -> None:
        """Define a DataFrame with example process data

        The returned DataFrame includes an init process, a mix of (non)orphaned
        processes, and multiple user IDs.
        """

        self.testing_data = pd.DataFrame({
            'PID': [INIT_PROCESS_ID, 100, 101, 102, 103],
            'PPID': [0, INIT_PROCESS_ID, INIT_PROCESS_ID, 100, 200],
            'PGID': [0, 1, 1, 2, 3],
            'UID': [0, 123, 123, 456, 789],
            'CMD': ['init', 'process_1', 'process_2', 'process_3', 'process_4']})

    def test_empty_whitelist(self) -> None:
        """Test the returned DataFrame is empty when the whitelist is empty"""

        returned_df = include_user_whitelist(self.testing_data, [])
        self.assertTrue(returned_df.empty)

    def test_whitelisted_by_id(self) -> None:
        """Test the returned UID values against a whitelist of explicit ID values"""

        whitelist = (123, 456)
        returned_df = include_user_whitelist(self.testing_data, whitelist)
        self.assertTrue(set(returned_df['UID']).issubset(whitelist))

    def test_whitelisted_by_id_range(self) -> None:
        """Test the returned UID values against a whitelist of ID ranges"""

        whitelist = (1, 2, (100, 500))
        returned_df = include_user_whitelist(self.testing_data, whitelist)
        self.assertCountEqual(returned_df['UID'].unique(), {123, 456})
