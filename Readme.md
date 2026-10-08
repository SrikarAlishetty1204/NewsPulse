# NewsPulse

A daily news digest that runs on your own PC. NewsPulse reads RSS feeds, uses a local LLM to select and summarize the categories you care about, stores the results in SQL Server, and emails you a daily digest.

It requires no gpu or AI APIs(can be added for faster working). The only credential required is a Gmail App Password if you want to send the digest by email.

## How It Works

```text
RSS feeds
    │
    ▼
Check saved URLs
    │
    ▼
Categorize with local LLM
    │
    ├── unwanted category ──► skip
    │
    ▼
Download article
    │
    ▼
Extract article text
    │
    ▼
Summarize + rate importance
    │
    ▼
Save to SQL Server
    │
    ▼
Send daily digest
```

### What a run does

1. **Fetch** — Reads the latest entries from the configured RSS feeds.
2. **Deduplicate** — Removes URLs that are already stored in the database or have already been seen during the current run.
3. **Categorize** — Uses a local Ollama model to classify each new headline into one of the configured categories.
4. **Filter** — Only articles belonging to the configured wanted categories are processed further.
5. **Download** — Downloads the selected articles and extracts their main text using `trafilatura`.
6. **Summarize** — The LLM generates a 3–4 sentence summary and assigns an importance score from 1–10.
7. **Store** — Saves the processed articles and summaries to SQL Server.
8. **Email** — Builds a digest grouped by category, with the most important articles shown first.

## Application Flow

`main.py` acts as the entry point and orchestrates the complete pipeline.

When started, it:

1. Loads configuration from `.env`.
2. Checks whether NewsPulse has already completed successfully today.
3. Checks available system RAM before starting the local model workload.
4. Keeps Windows awake while the process is running.
5. Loads previously saved article URLs from SQL Server.
6. Passes those URLs to the news service so known articles can be skipped before any LLM calls.
7. Fetches, categorizes, filters, downloads, and summarizes new articles.
8. Saves the resulting articles to SQL Server.
9. Sends the email digest.
10. Records the successful run date.
11. Logs failures and exits with a non-zero status if something goes wrong.

The main application flow is intentionally kept in `main.py`, while individual responsibilities are separated into services:

```text
main.py
   │
   ├── database.py
   │      └── Read saved URLs / Save articles
   │
   ├── news_service.py
   │      └── Fetch → Categorize → Download → Summarize
   │
   ├── mail_service.py
   │      └── Build and send digest
   │
   └── logger.py
          └── Application logging
```

This separation keeps the entry point small and makes the individual parts of the pipeline easier to test and maintain.

## Scheduling

NewsPulse is designed to run unattended using an operating-system scheduler such as **Windows Task Scheduler**.

The scheduler is responsible only for starting the application. The application itself handles the conditions required for a successful run.

Before doing any work, `main.py`:

- Checks whether a successful run has already happened today.
- Checks whether enough RAM is available for the local LLM.
- Exits with a failure status when the system is not ready, allowing the scheduler to retry later.
- Keeps the computer awake while processing.
- Records the date only after the entire pipeline completes successfully.

This means the scheduling configuration can be changed independently of the application. For example, you can configure Task Scheduler to start NewsPulse once a day, periodically retry it, or start it after the computer wakes from sleep.

## Tech Stack

| Part | Used for |
|---|---|
| Python 3.11 | Application and processing pipeline |
| Ollama (`gemma4:e4b`) | Local categorization and summarization |
| SQL Server + ODBC Driver 18 | Article storage |
| `pyodbc` | SQL Server connectivity |
| `feedparser` | RSS feed parsing |
| `requests` | Downloading articles |
| `trafilatura` | Extracting article text |
| Gmail SMTP (`smtplib`) | Sending the digest |
| Windows Task Scheduler | Unattended execution |
| PowerShell | Optional Windows notification script |

## Project Layout

```text
src/
  main.py             Entry point and application orchestration
  news_service.py     RSS fetching, categorization, downloading and summarization
  database.py         SQL Server access and article persistence
  mail_service.py     Digest generation and email delivery
  logger.py           Logging to file and console
  test_service.py     Dry run without database or email

scripts/
  notify_before_run.ps1
                      Optional Windows reminder notification

Commands.sql          Database/table definitions and initial categories
.env.example          Configuration reference with comments
how_to_run.md         Setup, manual execution, scheduling and troubleshooting
```

## Configuration

NewsPulse is configured through environment variables in `.env`.

The included `.env.example` documents the available settings, including:

- RSS feed URLs
- News categories
- Wanted categories
- Ollama model
- SQL Server connection details
- Email configuration
- Minimum available RAM

Copy `.env.example` to `.env` and update the values for your environment.

## Running Manually

NewsPulse can be run directly without the scheduler:

```bash
python -m src.main
```

This is useful for testing the complete pipeline or running the digest on demand.

A separate dry-run service is also available for testing the news-processing flow without writing to the database or sending email.

## Local-First

NewsPulse is designed around a local-first workflow:

- RSS feeds provide the source articles.
- Ollama runs the LLM locally.
- SQL Server stores the collected data locally.
- No external AI API key is required.
- Email is only sent when the Gmail SMTP configuration is enabled.

This makes NewsPulse useful as a personal news system that can continue running without depending on paid AI APIs or cloud-hosted inference.

## Setup

See **[how_to_run.md](how_to_run.md)** for:

- Installing dependencies
- Setting up Ollama
- Creating the SQL Server database
- Configuring `.env`
- Configuring Gmail SMTP
- Running NewsPulse manually
- Setting up Windows Task Scheduler
- Troubleshooting common issues