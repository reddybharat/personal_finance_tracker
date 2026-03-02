"""Shared UI helpers for the Streamlit app (error messages, connection checks)."""

SUPABASE_ERROR_MSG = (
    "**Could not reach Supabase.** This is usually:\n\n"
    "• **Project paused** — Free-tier projects pause after inactivity. "
    "Open your [Supabase Dashboard](https://supabase.com/dashboard), select the project, and click **Restore**.\n\n"
    "• **Temporary outage** — Try again in a few minutes.\n\n"
    "• **Network/firewall** — Check VPN or corporate network if the problem continues."
)


def is_supabase_connection_error(err: str) -> bool:
    return "525" in err or "SSL handshake" in err or "JSON could not be generated" in err
