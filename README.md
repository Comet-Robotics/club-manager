# clubManager

clubManager is a web app for managing all things related to club operations. Some of the things it does include:

- Link shortener
- Event check-ins / meeting attendance tracking
- Payment system for member dues and other ad-hoc payments (ex: club shirts), backed by Square
- Discord role management based on membership status
- Discord bot as an alternative interface for some of the above features

## dev setup 
needs to be fleshed out, the deployment section will probably be helpful

first, install deps and create virtualenv: `pipenv install`
obtain the config.ini from Jason or Mason for Square, place at root of project

## deployment

### first time setup
you'll need to install python 3.11 (preferably via [pyenv](http://github.com/pyenv/pyenv?tab=readme-ov-file)), [pipenv](https://pipenv.pypa.io/en/latest/#install-pipenv-today), [nodejs](https://nodejs.org/en) (preferably via [nvm](http://github.com/nvm-sh/nvm?tab=readme-ov-file)), nginx, and postgresql before continuing. this assumes you are deploying on some debian-based system.

for a production deployment, you'll need to install pipenv globally as opposed to just for the current user which is recommended in pipenv docs: `sudo apt install pipenv`. this is so that the pipenv binary is accessible in the systemd services.

once pipenv is installed, run `./deploy/init.sh` (sets up systemd services, does not start them).

### useful commands
- run server: `pipenv run python manage.py runserver`
- run migrations: `pipenv run python manage.py migrate`
- create migrations: `pipenv run python manage.py makemigrations`
- create the shared cache table as an UNLOGGED table (run after migrating a fresh database): `pipenv run python manage.py setup_cache_table`
- run static: `pipenv run python manage.py collectstatic`
- create superuser: `pipenv run python manage.py createsuperuser`
- send any queued email right now instead of waiting for the timer: `pipenv run python manage.py send_queued_mail`
- delete stored email older than 90 days: `pipenv run python manage.py cleanup_mail --days 90 --delete-attachments`

to \[re-\]deploy: `./deploy/run.sh` (does not include pulling from git)

#### viewing logs
- `journalctl -e -u gunicorn.service`
- `journalctl -e -u gunicorn.socket`
- `journalctl -e -u discord_bot.service`
- `journalctl -e -u post_office_queue.service`
- `journalctl -e -u post_office_cleanup.service`

## email

Outgoing email goes through [django-post_office](https://github.com/ui/django-post_office), which
stores every message in the database before handing it to the real backend (SMTP in production,
[naomi](https://github.com/AndrewIngram/django-naomi) locally when the `SMTP_*` environment
variables aren't all set). That means the admin has a **Post Office** section where you can read
any message we have ever sent, see the delivery attempts for it, and resend one - useful when a
member says they never got their account link email.

- messages are sent inline, during the request or bot command that created them, so nothing waits
  on a timer. The queue is only used for scheduled mail, retries, and the admin's "requeue"
  action, and the `post_office_queue` systemd timer drains it every 5 minutes.
- every message gets a `Message-ID` generated from `PUBLIC_URL`'s hostname and stored alongside
  it, so the ID in the admin is the one to search for in the SMTP provider's logs.
- the `post_office_cleanup` timer drops stored messages older than 90 days, so the tables don't
  grow forever.
- message bodies are rendered from the Django templates in `core/templates/email/` by
  `core.emails`, not from post_office's database-stored templates - that admin page is hidden
  because nothing reads it.

## error reporting

Unhandled errors, `logging` calls at `ERROR` or above, traces, and profiles are reported
to Sentry. Both processes are covered: the Django site, and the Discord bot along with
the FastAPI server it runs alongside the bot client.

**Sentry never runs in local development.** It is skipped entirely whenever `DEBUG` is
on, so there is nothing to configure — or to accidentally pollute the issue feed with —
while working locally.

Every instance reports to Comet Robotics' shared Sentry project by default, so a
deployment is debuggable without any per-instance setup. Events carry two tags that keep
them separable:

- `tenant` — which deployment the event came from. Defaults to the `PUBLIC_URL` hostname;
  override with `SENTRY_TENANT` for a friendlier name.
- `service` — `web` or `discord-bot`.

Tracing runs in Sentry's **stream mode** (`trace_lifecycle="stream"`): spans are sent in
batches as they finish rather than buffered until the root span closes, which lifts the
1000-span-per-transaction cap and surfaces trace data sooner. Two consequences worth
knowing if you write custom instrumentation:

- The legacy `sentry_sdk.start_span` / `start_transaction` API is a no-op in stream mode
  and returns a `NoOpSpan`. Use the streamed Span API instead. We currently rely entirely
  on auto-instrumentation, all of which is stream-aware.
- Scope tags don't reach spans, because spans are their own envelope items. The tenant and
  service are stamped on via `before_send_span` — which itself only works in stream mode.

To point an instance at its own Sentry project, set `SENTRY_DSN`. To opt out of reporting
altogether, set `SENTRY_ENABLED=0` (or blank out `SENTRY_DSN`). The rest of the knobs are
listed in `.env.example`.

### sampling and quota

Traces and profiles are both metered by Sentry, so they sample below 1.0 by default:
`SENTRY_TRACES_SAMPLE_RATE` at 0.2 and `SENTRY_PROFILE_SESSION_SAMPLE_RATE` at 0.5. Note
that the Sentry onboarding wizard suggests 1.0 for both — that is a demo value chosen to
surface data immediately, not a production setting.

Errors and logs are **not** sampled; every one is reported.

Continuous profiling is the expensive one: Sentry's free Developer plan includes **zero**
continuous profile hours, so any profiling at all trips the billing quota until the org is
on a plan that covers it. Set `SENTRY_PROFILE_SESSION_SAMPLE_RATE=0` to switch profiling
off without touching anything else.

### error pages and reference codes

The 400/403/404/500 pages show the Sentry event ID of whatever was just captured. When a
user reports a problem and quotes that code, searching for it in Sentry goes straight to
the event, with the request, the signed-in user, and the preceding log lines attached.

These pages are deliberately standalone — they don't extend the portal base template,
which reads `ServerSettings` from the database. An error page has to render when the
database is exactly what's broken.

### releases and suspect commits

Events are always tagged with a release: with `SENTRY_RELEASE` unset, the SDK auto-detects
it as the current commit SHA of the checkout the services run from. That much needs no
setup.

Registering that release *with* Sentry is what buys the rest — suspect commits ("this was
probably introduced by commit X"), working `resolvedInNextRelease`, deploy markers on
charts, and release-over-release comparison.

**Setting `SENTRY_AUTH_TOKEN` in `.env` is the only step.** It needs the
`project:releases` scope; `SENTRY_ORG` and `SENTRY_PROJECT` default to
`comet-robotics` / `club-manager`, matching the default DSN. Both `deploy/init.sh` and
`deploy/run.sh` install `sentry-cli` themselves the first time they see a token and then
verify it authenticates, so adding Sentry to an existing deployment doesn't mean
re-running `init.sh` — the next `run.sh` picks it up.

That the token *exists* is the signal, rather than a hostname check or a separate flag: an
instance with a release token is an instance that wants releases. A club running its own
copy sets no token, so nothing is installed and nothing is reported. To force the decision
the other way, set `SENTRY_CLI_INSTALL` to a truthy or falsy value; to avoid tracking the
latest CLI, pin `SENTRY_CLI_VERSION`.

Nothing here can fail a deploy. A missing token, a failed install, a rejected token, or a
Sentry outage each print a warning and continue. The release is registered before the
services restart; the deploy marker is recorded after they come back up, so its timestamp
reflects when the new code started serving.

The release SHA comes from `git rev-parse HEAD` rather than
`sentry-cli releases propose-version`, specifically so it cannot disagree with the SHA the
SDK auto-detects.

### checking that a deployment reports

Because Sentry is off under `DEBUG`, the wiring can only be exercised on a real
deployment. Set `SENTRY_DEBUG_ENDPOINT=1`, restart, and visit `/sentry-debug/` — it
raises on purpose. Unset it afterwards.

