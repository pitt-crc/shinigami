"""Tests for the `utils.include_user_whitelist` function."""

from unittest import TestCase

import pandas as pd

from shinigami.utils import include_user_whitelist


class UserIDs(TestCase):
    """Test the identification of whitelisted user IDs from a DataFrame of process data"""

    def setUp(self) -> None:
        """Define a DataFrame with example process data

        The returned DataFrame includes an init process, a mix of (non)orphaned
        processes, and multiple user IDs.
        """

        self.testing_data = pd.DataFrame({'UID': [0, 123, 123, 456, 789]})

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
