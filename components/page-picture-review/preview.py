#!/usr/bin/env python3
"""The fast loop: rebuild the demo, serve it, tell you if it would publish clean.

    python3 preview.py <cpk-root> --state <page-dir> [--no-build] [--port 4174] [--no-check]

For anyone with write access to both repos who wants to SEE a change now, without
going near an artifact. Regenerates the demo, makes sure a server is running at
the right root, and prints a cache-busted URL. `--no-build` skips campaign-build
and reuses `_site`, which is the difference between about twenty seconds and one.

It also runs the publish gate (`bundle.py check`) by default and prints PASS or
FAIL. That costs about a second and needs no artifact: the point is that the
answer to "would this publish correctly?" arrives during the fast loop, not
twenty minutes later when a reviewer opens a page with no fonts.

Two traps this exists to close, both met on 2026-09-18:

  1. A server started in an earlier session OUTLIVES it. One ran for two hours
     serving a path whose worktree had been moved out from under it — the URL
     kept answering while the page it served was gone. So this checks what is
     actually bound to the port and refuses to trust a wrong one.
  2. The server must be rooted at the REPO, not at `review/`. The demo reaches
     its pictures as `../<kit>/src/...`, above the review folder; serving
     `review/` puts every picture outside the root and the page loads fine with
     all 90 of them missing, which looks like a broken build and is not one.
"""
import os, re, subprocess, sys, tempfile, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def server_on(port):
    """The --directory of the http.server bound to `port`, or None."""
    ps = subprocess.run(['ps', '-axo', 'command'], capture_output=True, text=True).stdout
    for line in ps.splitlines():
        if f'http.server {port}' in line and '--directory' in line:
            return line.split('--directory', 1)[1].strip().split()[0]
    return None


def main(argv):
    def opt(name, default=None):
        if name in argv:
            i = argv.index(name); v = argv[i + 1]; del argv[i:i + 2]; return v
        return default
    no_build = '--no-build' in argv and not argv.remove('--no-build')
    no_check = '--no-check' in argv and not argv.remove('--no-check')
    port = int(opt('--port', '4174')); page = opt('--page')
    state = opt('--state')
    slug = opt('--slug')
    if not argv or not state:
        sys.exit(__doc__)
    repo = os.path.abspath(argv[0])

    import json
    cfg = json.load(open(os.path.join(state, 'page.json')))
    slug = slug or cfg['slug']; page = page or cfg['page']
    cmd = [sys.executable, os.path.join(HERE, 'make_demo.py'),
           os.path.join(repo, cfg['kit']), '--out', os.path.join(repo, 'review'),
           '--slug', slug, '--page', page, '--state', os.path.abspath(state)]
    if no_build:
        cmd.append('--no-build')
    print('$ ' + ' '.join(cmd[1:]))
    if subprocess.run(cmd).returncode:
        sys.exit('make_demo.py failed — nothing regenerated')

    demo = os.path.join(repo, 'review', '_preview-landing.html')

    if not no_check:
        # staged outside the repo on purpose — a throwaway copy of 95 assets has
        # no business sitting in a folder someone is about to `git add`
        out = os.path.join(tempfile.gettempdir(), f'preview-bundle--{slug}--{page}')
        subprocess.run(['rm', '-rf', out])
        r = subprocess.run([sys.executable, os.path.join(HERE, 'bundle.py'), 'stage', demo,
                            os.path.join(repo, cfg['kit'], 'src', slug, 'assets'), '--out', out,
                            '--state', os.path.abspath(state)],
                           capture_output=True, text=True)
        tail = [l for l in r.stdout.splitlines() if l.strip()][-1:]
        print(f'\npublish gate : {"PASS" if r.returncode == 0 else "FAIL"}  — {tail[0] if tail else ""}')
        if r.returncode:
            print(r.stdout)
            print('  ^ this would publish broken. Fix before making an artifact.')

    bound = server_on(port)
    if bound is None:
        subprocess.Popen([sys.executable, '-m', 'http.server', str(port),
                          '--bind', '127.0.0.1', '--directory', repo],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        print(f'server       : started, rooted at {repo}')
    elif os.path.realpath(bound) != os.path.realpath(repo):
        print(f'\nWRONG SERVER on :{port} — it serves {bound}, not {repo}')
        print(f'  kill it and rerun:  pkill -f "http.server {port}"')
        sys.exit(1)
    else:
        print(f'server       : already running, rooted at {bound}')

    url = f'http://127.0.0.1:{port}/review/_preview-landing.html?v={int(time.time())}'
    try:
        code = urllib.request.urlopen(url, timeout=5).getcode()
    except Exception as e:                       # noqa: BLE001 — report, don't raise
        sys.exit(f'server did not answer: {e}')
    print(f'\n{url}   (HTTP {code})')
    print('the ?v= is the cache-buster — http.server caches hard, so use this URL, not the bare one')


if __name__ == '__main__':
    main(sys.argv[1:])
