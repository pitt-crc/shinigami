import unittest

import asyncssh


class TestGetRemoteProcesses(unittest.IsolatedAsyncioTestCase):

    async def test_get_remote_processes(self):
        async with asyncssh.connect('localhost') as conn:
            pass
