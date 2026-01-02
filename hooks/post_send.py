#!/usr/bin/env python3
"""Post-send reminder about pending acks."""

import os

project = os.environ.get("PROJECT_DIR") or os.environ.get("AGENT_MAIL_PROJECT") or os.getcwd()

print("")
print("💡 Remember to check for acknowledgements:")
print(f"   agent-mail acks pending \"{project}\" <your-agent-name>")
print("")
