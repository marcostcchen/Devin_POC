"""Business configuration, resolved once at import time from the environment."""

import os

#: Requests at or above this amount need a finance approver's sign-off, whoever
#: raised them. It is the one rule the whole app is built around, so it is
#: configuration rather than a constant.
APPROVAL_THRESHOLD_AMOUNT = float(os.environ.get("APPROVAL_THRESHOLD_AMOUNT", "200"))

#: Synthetic requests generated on first start.
SEED_REQUEST_COUNT = int(os.environ.get("SEED_REQUEST_COUNT", "23"))
