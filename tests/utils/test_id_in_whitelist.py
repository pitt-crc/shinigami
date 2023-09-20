"""Tests for the ``utils.id_in_whitelist`` function"""

from unittest import TestCase

from shinigami.utils import id_in_whitelist


class Whitelisting(TestCase):
    """Test ID values are correctly whitelisted"""

    def test_empty_whitelist(self) -> None:
        """Test the return value is ``False`` for all ID values when the whitelist is empty"""

        self.assertFalse(id_in_whitelist(0, []))
        self.assertFalse(id_in_whitelist(123, []))

    def test_whitelisted_by_id(self) -> None:
        """Test return values for a whitelist of explicit ID values"""

        whitelist = (123, 456, 789)
        self.assertTrue(id_in_whitelist(456, whitelist))
        self.assertFalse(id_in_whitelist(0, whitelist))

    def test_whitelisted_by_id_range(self) -> None:
        """Test return values for a whitelist of ID ranges"""

        whitelist = (0, 1, 2, (100, 300))
        self.assertTrue(id_in_whitelist(123, whitelist))
        self.assertFalse(id_in_whitelist(301, whitelist))
