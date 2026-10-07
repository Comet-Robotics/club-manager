# Club Manager

Club Manager is a web app and Discord bot for managing all things related to Comet Robotics club operations. Some of the things it does include:

- Link shortener
- Event check-ins / meeting attendance tracking
- Payment tracking for credit card and cash payments (for member dues and other ad-hoc payments, like club shirts)
- Processing credit card payments (by integrating [Square's API](https://developer.squareup.com/us/en/online-payment-apis))
- Assigning Discord roles to users based on membership status

It's also used by RoboSub who hosts their own instance of Club Manager.

## Technical Details

This app is written in Python using the Django web framework. [This page](https://www.djangoproject.com/start/) has a decent overview of what Django offers which you should read over - its a less than 5 min read). We use PostgreSQL as the database.

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

Now download ("clone") your own copy of Club Manager into a folder of your choice - your Documents folder or wherever you keep projects is fine as long as it doesn't get synced by a cloud storage provider like OneDrive or iCloud Drive.

```sh
git clone https://github.com/Comet-Robotics/club-manager.git
cd club-manager
```

Everything below should run from inside this `club-manager` folder.

### System Prerequisites

To work on Club Manager, you'll need to install some more software. We'll walk you through installing everything in the next section. 

- **PostgreSQL 14**: database engine that stores all Club Manager data
- **Python 3.11.11**: programming language that Club Manager's backend is written in. you **must have this specific version installed** - newer versions have bugs with the Django version we're using, and older ones aren't compatible with some Python language features we use.
- **Pipenv**: this is our **package manager** and **virtual environment manager**
  - **package manager**: a tool that takes a list of all the external Python libraries that our code depends on ([here's the list if you're curious](./Pipfile)), and downloads them for us. 
  - **virtual environment manager**: pipenv automatically creates virtual environments - which are a mechanism to make sure that every project has its own folder for storing its external libraries, isolated from any other projects. this is important because without virtual environments, when you run `pip install django==5.1` you install django 5.1 **globally** - for every program or project on your computer that uses python. this can cause issues if, for example, one project on your computer needs django 5.1, but another needs django 6. 

### Installing System Prerequisites Using `mise`

`mise` is a tool that helps with installing software on your computer. Here, we'll use it to install the correct versions of Python and pipenv. `mise` installs specific software versions from a list (see [mise.toml](./mise.toml) and [.python-version](./python-version)), making sure that every developer's development environments should be running the same software versions, installed the same way as each other and as our production server. 

Having everyone's development environment set up the exact same way, with the same versions which makes it easier to troubleshoot and reproduce issues locally, because we can generally eliminate environmental differences as a potential source of issues.

<details>
<summary>ok but what if i already have python and/or pipenv installed differently...</summary>

If you have python and/or pipenv installed on your computer already, or want to install it manually instead of using `mise`, you _can_ do that, but I (Jason) personally would not recommend this and don't intend to help people who have dev environment issues who do this, for the reasons mentioned above and for my own sanity. sorry not sorry :see_no_evil:
</details>

Follow the steps on [this page](https://mise.jdx.dev/getting-started.html) to install `mise`. Once you're done, close and reopen your terminal.

Then run these commands while in your clone of club-manager:

```sh
mise trust      # one-time: marks this repo's mise config as safe to run
mise run new-developer-setup  # automatically installs system prereqs mentioned above. then runs the setup command which does a lot: helps you get your git logged in, installs dependencies using pipenv, creates your .env, sets up the database, creates a default admin login
```

Once that's done, run `mise run server` and you should officially be up and running!

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

