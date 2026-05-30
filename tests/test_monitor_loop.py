import unittest
from unittest.mock import patch

import monitor_loop


class MonitorLoopTests(unittest.TestCase):
    def setUp(self):
        monitor_loop.SENT_REENTRY_ALERT = False

    def test_alert_fires_once_when_vix_drops_below_threshold(self):
        with patch("monitor_loop.send_telegram") as send:
            state = monitor_loop.check_reentry(18.9)
            self.assertTrue(state)
            send.assert_called_once()

            # Should not spam while still below threshold.
            state_again = monitor_loop.check_reentry(18.8)
            self.assertTrue(state_again)
            send.assert_called_once()

    def test_alert_resets_after_vix_rebounds(self):
        with patch("monitor_loop.send_telegram") as send:
            monitor_loop.check_reentry(18.5)
            self.assertTrue(monitor_loop.SENT_REENTRY_ALERT)

            # Re-arm the alert once VIX rises above threshold + 2.
            state = monitor_loop.check_reentry(21.5)
            self.assertFalse(state)

            # Should fire again on next drop.
            state = monitor_loop.check_reentry(18.7)
            self.assertTrue(state)
            self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
