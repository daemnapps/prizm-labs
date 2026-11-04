"""Opt-in bridge to the existing run-kit. No provider is selected here."""
from pathlib import Path


def run_kit_handler(chain_factory, step_key, fields):
    """Wrap a caller-configured Chain stage as a pilot draft handler.

    chain_factory(job) returns a run_kit.stage.Chain in a job/revision-scoped
    output directory. fields(job) supplies that chain's existing prompt inputs.
    The caller owns its model credentials, allowance and approved brand scope.
    Nothing here approves the output or registers a production chain by default.
    """
    def produce(job):
        chain = chain_factory(job)
        if chain.dry:
            raise ValueError('A dry-run placeholder is not a reviewable artifact')
        chain.run(step_key, **fields(job))
        step = chain.steps[step_key]
        artifact = Path(chain.out) / (step_key + '--' + step['label'] + '.md')
        if not artifact.is_file() or not artifact.read_bytes():
            raise ValueError('Run-kit stage did not produce a reviewable artifact')
        return artifact
    return produce
