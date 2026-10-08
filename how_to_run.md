# How to run NewsPulse

These steps are for Windows 10/11. Commands are for PowerShell.

## 1. Install the prerequisites

| Install | Notes |
|---|---|
| [Python 3.11](https://www.python.org/downloads/) | |
| [Ollama](https://ollama.com/download) | Used to run the local LLM |
| SQL Server (Express or Developer) | Uses Windows authentication |
| [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) | `pyodbc` connects through it |
| A Gmail account with **2-Step Verification** enabled | Required to create a Gmail App Password |

Then download the model:

```powershell
ollama pull gemma4:e4b
```

The model runs in RAM unless you have a suitable dedicated GPU, so plan for roughly **10 GB of free RAM** during a run.

## 2. Set up the project

```powershell
git clone <repo-url> newsPulse
cd newsPulse

python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

## 3. Create the database

In SQL Server Management Studio (or `sqlcmd`):

```sql
CREATE DATABASE NewsPulse;
GO

USE NewsPulse;
GO
```

Then run the `CREATE TABLE` statements and the `INSERT INTO Categories` statement from `Commands.sql`.

The category names in the database must match the categories configured in `.env`.

## 4. Create a Gmail App Password

1. Turn on 2-Step Verification in your Google Account.
2. Open the Google App Passwords page.
3. Create an app password for NewsPulse.
4. Copy the generated 16-character password.
5. Password to be used without any spaces

Your normal Gmail password will not work with Gmail SMTP. NewsPulse expects an App Password.

## 5. Configure `.env`

Create the environment file:

```powershell
copy .env.example .env
```

Then configure the required values.

| Setting | Example | Meaning |
|---|---|---|
| `DB_SERVER` | `localhost\SQLEXPRESS` | Your SQL Server instance |
| `DB_NAME` | `NewsPulse` | Database created above |
| `SMTP_USER` | `you@gmail.com` | Account that sends the email |
| `SMTP_PASSWORD` | `abcdefghijklmnop` | Gmail App Password |
| `MAIL_TO` | `you@gmail.com` | Address that receives the digest |

Other useful settings:

| Setting | Meaning |
|---|---|
| `RSS_URLS` | Comma-separated RSS feed URLs |
| `CATEGORIES` | Categories the LLM can assign |
| `WANTED_CATEGORIES` | Categories that are downloaded, summarized and mailed |
| `MAX_ENTRIES_PER_FEED` | Maximum number of entries read from each feed |
| `DEBUG` | Set to `true` for detailed logging |
| `MIN_FREE_RAM_GB` | Minimum available RAM required before starting a run |
| `TRIM_TEXT` / `TRIM_SIZE` | Optionally reduce long article text before summarization |

`.env` is included in `.gitignore`. **Never commit it**, because it contains credentials such as your Gmail App Password.

## 6. Run NewsPulse

### Dry run

The dry run processes the news pipeline without writing to SQL Server or sending email.

Results are written to:

```text
output/articles.txt
```

Run it with:

```powershell
venv\Scripts\python -m src.test_service
```

This is useful for checking RSS feeds, categorization, article extraction and summarization before enabling the full pipeline.

### Full run

Run the complete pipeline with:

```powershell
venv\Scripts\python -m src.main
```

The application performs the following steps:

```text
main.py
  │
  ├── Check whether it already ran successfully today
  ├── Check available RAM
  ├── Keep Windows awake during processing
  │
  ├── Load saved URLs from SQL Server
  │
  ├── Fetch and process new articles
  │     ├── Categorize
  │     ├── Filter unwanted categories
  │     ├── Download article
  │     └── Summarize + score
  │
  ├── Save articles to SQL Server
  ├── Send email digest
  └── Record successful run
```

### Important behavior

**Once per day**

After a successful run, NewsPulse writes the current date to:

```text
logs/last_run.txt
```

If the application is started again on the same day, it exits without processing anything.

To manually run it again:

```powershell
Remove-Item logs\last_run.txt
venv\Scripts\python -m src.main
```

**Low RAM**

If available RAM is below `MIN_FREE_RAM_GB`, the application exits without running the model.

This allows an external scheduler to start it again later.

**Duplicate articles**

URLs already stored in SQL Server are skipped before any LLM processing.

**Verbose logging**

For detailed logging during a single run:

```powershell
$env:DEBUG="true"
venv\Scripts\python -m src.main
```

## 7. Schedule NewsPulse

NewsPulse can be run unattended using **Windows Task Scheduler**.

The scheduler is responsible for **starting `main.py`**. NewsPulse itself is responsible for deciding whether the conditions are suitable for processing.

This separation means you can choose your own schedule without changing the application.

For example, Task Scheduler can:

- Start NewsPulse once a day.
- Start it periodically so failed attempts can be retried.
- Wake the PC from sleep.
- Start the application when the computer becomes available.
- Prevent multiple instances from running at the same time.

### Recommended scheduling model

A useful setup is to schedule NewsPulse to start periodically during a time window.

For example:

```text
Task Scheduler
      │
      ├── Start NewsPulse
      │
      ▼
   main.py
      │
      ├── Already ran today?
      │       └── Yes → Exit
      │
      ├── Enough RAM?
      │       └── No → Exit
      │
      └── Run news pipeline
```

Because `main.py` records the date only after a successful run, starting it multiple times is safe.

This also means the scheduler can retry after conditions such as low memory or temporary network problems.

### Create a scheduled task

Replace the paths and schedule below with values appropriate for your machine.

For example:

```powershell
$project = "C:\path\to\newsPulse"
$python = "$project\venv\Scripts\pythonw.exe"

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument "-m src.main" `
    -WorkingDirectory $project

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At 2:30PM

$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName "NewsPulse daily digest" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Run the NewsPulse daily news digest"
```

`pythonw.exe` is used so that scheduled runs do not open a console window.

If you prefer to see the console output while testing, use:

```powershell
venv\Scripts\python.exe -m src.main
```

### Retrying automatically

If you want the scheduler to retry NewsPulse during a time window, configure the task with a repetition interval.

For example, to start every 30 minutes for several hours:

```powershell
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At 2:30PM `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Hours 3)
```

The exact schedule is up to you.

NewsPulse will make sure only the first **successful** run of the day performs the actual work.

### Running while the PC is asleep

If you want Windows to wake the PC for the scheduled task, enable wake timers:

**Control Panel → Power Options → Change plan settings → Change advanced power settings → Sleep → Allow wake timers**

Enable them for the appropriate power modes.

A locked computer can run the task. A computer that is completely shut down cannot.

### Optional notification

You can optionally use:

```text
scripts/notify_before_run.ps1
```

to show a reminder before the NewsPulse task starts to free up ram .

This is not required for NewsPulse itself and can be omitted if you want the application to run completely silently.

### Managing the scheduled task

Run the task immediately:

```powershell
Start-ScheduledTask -TaskName "NewsPulse daily digest"
```

Check its status:

```powershell
Get-ScheduledTaskInfo -TaskName "NewsPulse daily digest"
```

Remove it:

```powershell
Unregister-ScheduledTask `
    -TaskName "NewsPulse daily digest" `
    -Confirm:$false
```

Changes to `.env` or the application code are picked up the next time the task starts.

If you change the task's schedule, update or re-register the scheduled task.

## 8. Check what happened

NewsPulse writes its logs to:

```text
logs/newspulse.log
```

To view the most recent entries:

```powershell
Get-Content logs\newspulse.log -Encoding UTF8 -Tail 30
```

With `DEBUG=false`, the log contains mainly warnings and errors.

With `DEBUG=true`, it contains detailed progress information.

The date of the last successful run is stored in:

```text
logs/last_run.txt
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `only X GB RAM free, need Y GB` | Not enough RAM is available. Close applications or lower `MIN_FREE_RAM_GB`. |
| `SMTPAuthenticationError (535)` | Gmail App Password is incorrect, missing or revoked. |
| `no new entries in any feed` | Feeds contain no new entries, or the network was not ready yet. |
| `no new articles` | The fetched articles were already stored in the database. |
| ODBC / `pyodbc` connection error | Check `DB_SERVER`, SQL Server status and ODBC Driver 18 installation. |
| `ollama` connection error | Ollama is not running or the configured model is unavailable. |
| Scheduled task does not run | Check Task Scheduler history, task status and wake-timer settings. |
| Scheduled task runs but nothing happens | Check `logs/newspulse.log` and `logs/last_run.txt`. |
| Digest arrives in Spam | Mark the message as "Not spam". |
| Reminder does not appear | Windows notifications or Focus/Do Not Disturb may be blocking it. |