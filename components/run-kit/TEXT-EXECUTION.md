# Provider-neutral video writing

The existing prompts, order, and content checks stay in place. Text execution
is selectable without rewriting prompts or requiring an Anthropic account.

Supported integrations: teardown text stages, video-writing stages, copywriter
ad words, shared run-kit calls, and viewer text/image questions. The video
reader, transcription, image/video generation, and Gemini-based creative
review remain separate specialist services. This is not a claim that those
services have all been replaced or that every tool in the repo is migrated.

## Current-assistant execution

From the Prizm repo:

```sh
python3 components/run-kit/run_kit/text_executor.py run \
  --requests /private/run/text-requests --author codex -- \
  python3 tools/video-teardown/machine/line.py ai \
  --label existing-teardown --brand your-brand
```

The default executor is `session`. The same command with `--author claude`
uses a Claude session; neither label launches a provider or buys API tokens.
Each text stage leaves `request.json` and a readable `prompt.md`, then waits
for an answer. Read the entire prompt and inspect any attachments. Save only
the requested stage document in a text file, then submit it:

```sh
python3 components/run-kit/run_kit/text_executor.py answer \
  /private/run/text-requests/REQUEST_ID/request.json \
  --file /private/run/answer.md --author codex
```

Resume the original command. Exact answers are cached by request content,
including the system instructions, label, JSON requirement and image hash.
Changing the prompt/image creates a new request. A receipt names the actual
answer author and output hash. Transport acceptance is not a content-QC pass;
the original structure, hooks, swipe-match, manifest and viewer checks remain.

`pending DIRECTORY` lists unanswered requests. `PRIZM_TEXT_WAIT` optionally
waits for a session answer; its default is zero, so a runner returns promptly.
Legacy outer scripts can return nonzero while awaiting text; the request is
durable. Viewer checks may record a held state until their answers arrive.

## Unattended workers

Select `--executor command` and set `PRIZM_TEXT_COMMAND` to a JSON argv array,
for example `["python3", "/private/adapters/my_text_api.py"]`.
The adapter receives one JSON request on stdin and returns the stage document
on stdout, or valid JSON when `as_json` is true. It must inspect the attachment
paths when present. It chooses its provider/model and obtains credentials
securely. `PRIZM_TEXT_AUTHOR` identifies that adapter/model in receipts.

There is no shell evaluation, automatic retry, or silent provider fallback.
Failures surface to the caller. Per-request locks prevent concurrent workers
from submitting the same text request twice. Command mode currently uses
Mac/Linux `flock`; session mode is platform-independent. A worker interrupted
after a provider accepted a job but before saving its answer still requires
provider-specific reconciliation/idempotency in the adapter before retrying.

Without `PRIZM_TEXT_EXECUTOR`, old callers keep their legacy behavior. Use
the launcher above for a provider-neutral run. This switch propagates into
child processes, including the copywriter, and takes priority over legacy
Claude settings. No OpenAI or Anthropic API adapter has been configured by
this change; the current session is the live writer for the first test.

## Tests and publication

`install.py CHECKOUT` publishes the new module and narrow integration edits
from this source folder to a Prizm checkout. It refuses mismatched anchors.
In the source, run `PRIZM_TEST_REPO=CHECKOUT python3 -m unittest discover -s tools/text-executor`.
In the published checkout, run `python3 -m unittest discover -s components/run-kit/tests`.
Tests cover routing before legacy providers, prompt/image staleness, invalid
answers, command failures, cached resume, and concurrent consumers. Real API
generation and full creative-QC completion are separate integration checks.
