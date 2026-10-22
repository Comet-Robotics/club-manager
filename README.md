# Club Manager

Club Manager is a web app and Discord bot for managing all things related to Comet Robotics club operations. Some of the things it does include:

- Link shortener
- Event check-ins / meeting attendance tracking
- Payment tracking for credit card and cash payments (for member dues and other ad-hoc payments, like club shirts)
- Processing credit card payments (by integrating [Square's API](https://developer.squareup.com/us/en/online-payment-apis))
- Assigning Discord roles to users based on membership status

It's also used by RoboSub who hosts their own instance of Club Manager.

## Technical Details

This app is written in Python using the Django web framework. [This page](https://www.djangoproject.com/start/) has a decent overview of what Django offers which you should read over - its a less than 5 min read. We use PostgreSQL as the database.

For Comet Robotics, the app is deployed in a virtual machine on a server at our booth in the Makerspace. More details on the deployment and infrastructure stuff is on the CROUTON Committee ClickUp - to be added, ask an officer in Discord.


## Development Environment Setup

Want to contribute to Club Manager? You'll want to set up your own copy of Club Manager on your computer that you can use to make edits and test your changes - here's how to do that.

### Getting the repo on your computer

First you'll need **Git** (the tool that downloads our code and tracks changes to it):

To install Git follow the steps on the Download page at [git-scm.com](https://git-scm.com/install/) for your OS.

You'll also need a [GitHub account](https://github.com/signup). not to download the code, but to save your changes and open pull requests later.

Then tell Git who you are, so your changes are labeled with your name:

```sh
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Now download ("clone") your own copy of Club Manager into a folder of your choice - your Documents folder or wherever you keep projects is fine, as long as it doesn't get synced by a cloud storage provider like OneDrive or iCloud Drive.

```sh
git clone https://github.com/Comet-Robotics/club-manager.git
cd club-manager
```

Everything below should run from inside this `club-manager` folder.

### System Prerequisites

To work on Club Manager, you'll need to install some more software. We'll walk you through installing everything in the next section. 

- **PostgreSQL 14**: database engine that stores all Club Manager data
- **Python 3.11.13**: programming language that Club Manager's backend is written in. you **must have this specific version installed** - newer versions have bugs with the Django version we're using, and older ones aren't compatible with some Python language features we use.
- **Pipenv**: this is our **package manager** and **virtual environment manager**
  - **package manager**: a tool that takes a list of all the external Python libraries that our code depends on ([here's the list if you're curious](./Pipfile)), and downloads them for us. 
  - **virtual environment manager**: pipenv automatically creates virtual environments - which are a mechanism to make sure that every project has its own folder for storing its external libraries, isolated from any other projects. this is important because without virtual environments, when you run `pip install django==5.1` you install django 5.1 **globally** - for every program or project on your computer that uses python. this can cause issues if, for example, one project on your computer needs django 5.1, but another needs django 6. 

### Installing System Prerequisites Using [`mise`](https://mise.jdx.dev)

[`mise`](https://mise.jdx.dev) is a tool that helps with installing software on your computer. Here, we'll use it to install the correct versions of Python and pipenv. `mise` installs specific software versions from a list (see [mise.toml](./mise.toml) and [.python-version](./python-version)), making sure that every developer's development environments should be running the same software versions, installed the same way as each other and as our production server. 

Having everyone's development environment set up the exact same way, with the same software versions, makes it easier to troubleshoot and reproduce issues locally, because we can generally eliminate environmental differences as a potential source of problems.

<details>
<summary>ok, but what if i already have python and/or pipenv installed and don't want to reinstall?</summary>

i would still recommend installing using `mise`. `mise` will install its own isolated copies of python and pipenv separate from other installs of those tools on your system. it should not conflict with other installs on your system. 

However, if you really want to use existing installs or manage your installations some other way instead of using `mise`, you _can_ do that. the [mise.toml](./mise.toml) and [.python-version](./python-version) files specify the exact versions of these tools you should install. 

If you run into issues with Club Manager running with this setup, I (Jason) would recommend falling back to installing with `mise`. I don't intend to spend extensive amounts of time supporting dev environment issues caused by deviating from the steps above, for the reasons mentioned above and for my own sanity. sorry not sorry :see_no_evil:
</details>

Follow the steps on [this page](https://mise.jdx.dev/getting-started.html) to install `mise`. Once you're done, close and reopen your terminal.

Then run these commands after reopening your terminal:

- `cd club-manager`: move your terminal into your Club Manager clone. you'll need to tweak this command based on the file path you cloned the repository to.
- `mise trust`: this is a one time command that marks this repo's mise config as safe to run
- `mise run new-developer-setup`: automatically installs system prereqs mentioned above. then runs the setup command which does a lot: helps you get your git logged in, installs dependencies using pipenv, creates your .env, sets up the database, creates a default admin login

Once that's done, run `mise run server` and you should officially be up and running! Open the link that the command prints to your terminal (probably http://127.0.0.1:8000/) and login with the username and password that the setup command gave you previously.

From here on out, you can manage your local Club Manager instance through `mise exec` and `mise run`. Here's a sample of some commands you'll end up using as a developer.

```sh
mise run server                      # start the website
mise run bot                         # start the Discord bot

mise run manage -- makemigrations    # generates a new database migration
mise run manage -- migrate           # execute database migrations

mise tasks                           # see a list of all the `mise run ___` commands

mise exec -- pipenv install requests # one-off command with project tools: install a package
mise exec -- python --version         # one-off command with project tools: check the Python version
```

### Optional tools 

These are some additional tools you may want to install as well, but these are optional. These run on all desktop OSes.
- **TablePlus**: tool to visually interact with data in database engines, execute SQL queries, etc. [Download here.](https://tableplus.com)
- **Visual Studio Code**: simple code editor that most people use. Here's [a link to download it](https://code.visualstudio.com), but feel free to use the editor of your choice if you have a different one you prefer.

----

## Production Deployment Setup

> [!WARNING]
> This section needs some TLC. It works but is missing details most notably all the Postgres setup steps that need to happen after you install it, documentation of how we use Cloudflare Tunnel to expose Club Manager to the internet, and how we have auto deploys working via the self hosted github actions runner. would super appreciate anyone who'd want to put some love into properly documenting a production-ready Club Manager deployment

### first time setup
this assumes you are deploying on some debian-based system. you'll need nginx and postgresql, which
are system services and so aren't managed by this project: `sudo apt install curl nginx postgresql`.

run `./deploy/init.sh` (checks prerequisites, installs the toolchain, sets up systemd services;
does not start them). it's safe to re-run.

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

The pages extend the public base template, so they look like the rest of the portal
rather than being a separate design. That template reads the organization's name and
accent colour off `ServerSettings`, which lives in the database — and an error page has
to render when the database is exactly what's broken. So the error handlers pass a
transient, unsaved `ServerSettings` instead, which never queries and shows the model's
defaults. A regression test asserts zero queries to keep it that way.

### checking that a deployment reports

Because Sentry is off under `DEBUG`, the wiring can only be exercised on a real
deployment. Set `SENTRY_DEBUG_ENDPOINT=1`, restart, and visit `/sentry-debug/` — it
raises on purpose. Unset it afterwards.
