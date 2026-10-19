# social-distribution — post the content machine's output across your accounts

**Keys this tool needs:** GEELARK_API_TOKEN (or GEELARK_APP_ID + GEELARK_API_KEY), and one `PROXY_<NAME>` line per cloud phone. Put your own in `.env` at the top of the repo — see [`.env.example`](../../.env.example).

GeeLark runs real Android phones in its data center. Each one is its own
device, with its own phone number, model and location, so each social account
lives on its own phone. `geelark.py` drives those phones from one command:
checking proxies, making phones, and queueing TikTok, Instagram Reels and
YouTube Shorts posts on a schedule.

How to run several accounts properly: [`PLAYBOOK.md`](PLAYBOOK.md).

## The one thing that makes it work: the proxy

The phone runs in GeeLark's data center, not on your computer, so a VPN on
your laptop changes nothing. The platforms see the **phone's** connection. So
each phone needs its own proxy in the country you want to reach. Use a
residential or mobile proxy that keeps the **same IP** ("static" or "sticky"),
not a rotating or datacenter one. The phone's region, time zone and SIM follow
the proxy automatically.

The phone's language stays **English**. GeeLark's posting robot needs the
TikTok app in English (failure 20008 otherwise). Who sees your posts is decided
by the country, not the phone's language, and captions can be in any language.

## Setup, once per account

1. Get a GeeLark account and an API token: GeeLark app > Settings > API.
   Add `GEELARK_API_TOKEN=` to `.env`.
2. Buy one proxy per account (GeeLark sells them in the app, or use any
   residential provider). Add it to `.env` under a name you choose:
   `PROXY_DE_1=socks5://user:pass@host:port`
3. Check that it comes out where you need it:
   `python3 geelark.py check-proxy --proxy-key PROXY_DE_1 --country DE`
4. Make the phone. It refuses if the proxy is in the wrong country.
   `python3 geelark.py new-phone --name de-mybrand-tt-1 --proxy-key PROXY_DE_1 --country DE --group mybrand --tags tiktok de`
5. In the GeeLark app, open the phone, open TikTok (or Instagram/YouTube) and
   **log in by hand once**. Finish any code it sends you. Then leave the account
   to settle for a day before posting.
6. Keep that account on that phone only. Don't also log in from your own phone.

## Posting

One post (a file or a URL; `--at` is your computer's local time, default now):

```
python3 geelark.py post --phone de-mybrand-tt-1 --platform tiktok --video clip.mp4 --caption "..." --at 2026-10-21T18:00
```

A whole week: fill in a copy of [`plan-template.csv`](plan-template.csv), then

```
python3 geelark.py schedule my-week.csv --dry-run   # shows what it would queue
python3 geelark.py schedule my-week.csv             # queues it; saves task ids
python3 geelark.py status --file my-week.tasks.txt  # done / failed, and why, plus post links
```

Platforms: `tiktok`, `tiktok-carousel` (images joined by `|` in the video
column), `instagram` (Reels), `youtube` (Shorts; `title` column used).

## Checks

`python3 geelark.py doctor --proxy-key PROXY_DE_1` checks that the keys are in,
that GeeLark answers, and where each proxy comes out. It spends nothing.

## Costs to know

GeeLark charges per phone-minute (or a monthly price per phone) on top of its
plan. Proxies are billed by the proxy provider. Creating several phones in one
call needs GeeLark's Pro plan, so this tool makes them one at a time.
