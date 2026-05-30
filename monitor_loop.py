"""Simple VIX monitor loop helpers."""

from __future__ import annotations

LOW_VIX_THRESHOLD = 19.0  # The "Calm" zone
SENT_REENTRY_ALERT = False


def send_telegram(message: str) -> None:
    """Send a Telegram message.

    Replace this function body with your bot integration.
    """
    raise NotImplementedError("Implement Telegram bot send logic in send_telegram")


def check_reentry(current_vix: float) -> bool:
    """Fire/re-arm a VIX re-entry alert and return alert state."""
    global SENT_REENTRY_ALERT

    if current_vix < LOW_VIX_THRESHOLD and not SENT_REENTRY_ALERT:
        message = (
            f"🟢 **VIX RE-ENTRY ALERT**\n"
            f"Current VIX: {current_vix:.2f}\n"
            "Market has stabilized. Consider reloading the 'Fear' hedge with your "
            "VOO/VMFXX profits."
        )
        send_telegram(message)
        SENT_REENTRY_ALERT = True  # Prevent spamming
    elif current_vix > (LOW_VIX_THRESHOLD + 2.0):
        # Reset the alert once VIX climbs back up, so it can fire again next time it drops
        SENT_REENTRY_ALERT = False

    return SENT_REENTRY_ALERT
