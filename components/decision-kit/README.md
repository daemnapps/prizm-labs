# decision-kit

`decision.py` is an optional Typesafe adapter for classifying feedback scope.
It accepts text and returns a typed recommendation with usage and timing.
No function executes a tool, approves creative, publishes or rewrites a chain.

`request(text)` builds the versioned contract. `validate(response)` rejects
unknown models/labels, malformed probabilities and missing usage. `classify`
makes one bounded HTTP attempt; failures return `needs_review` without provider
error content. `suggested_route` maps accepted answers to candidate records only.

The caller owns key loading, persistent budget reservations and receipts.
The first caller is `tools/autonomy-pilot/pilot.py evaluate`; its README explains
the synthetic comparison and the limit of its confidence threshold.

Tests: `python3 -m unittest discover -s tools/autonomy-pilot/tests -v`.
