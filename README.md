# internship-autopilot

A local pipeline that collects new internship postings each day, filters out postings the user is not
eligible for, and generates a one-page resume tailored to each remaining posting. Results are tracked in
a static HTML dashboard and a spreadsheet.

The project runs entirely on the user's machine and requires only Python and LaTeX. It does not depend
on any AI service.

## Features

- Collection: reads the community-maintained [SimplifyJobs](https://github.com/SimplifyJobs) internship
  list and ranks postings by recency, then by a configurable list of priority companies.
- Job descriptions: retrieved through the public Greenhouse, Lever and Ashby posting APIs where
  available, with a plain HTML fallback.
- Eligibility filtering: rule-based checks for citizenship or security-clearance requirements, exclusion
  of F-1/CPT/OPT students, PhD-only roles, non-US locations and off-cycle terms. Postings that only state
  that visa sponsorship is not offered are kept and annotated.
- Resume tailoring: each bullet in the user's profile carries keywords; bullets are scored against the
  job title and description, and the highest-scoring material is added greedily until the page limit is
  reached, verified by compiling the LaTeX output. The tool selects and orders the user's own bullets and
  never generates new content.
- Tracking: a self-contained `Dashboard.html` with status tracking (To apply, Applied, OA, Interview,
  Offer, Rejected, Skipped) and an `applications.xlsx` summary, both regenerated on every run.
- Scheduling: a wrapper script for launchd (macOS) or cron (Linux) that runs once per day and catches up
  after the computer was asleep or powered off.

## Architecture

```
autopilot/
  sources.py   posting sources (SimplifyJobs) and job-description retrieval
  filters.py   title, location and eligibility rules; role classification
  tailor.py    keyword scoring, greedy page packing, LaTeX rendering and compilation
  tracker.py   de-duplication state, job records, status import, dashboard and spreadsheet output
  __main__.py  command-line interface and the daily run
templates/     LaTeX resume template and dashboard template
scripts/       daily wrapper script and launchd example
```

A daily run proceeds as follows:

1. Import any statuses saved from the dashboard.
2. Download candidate postings, drop previously seen ones, and rank the rest.
3. For each candidate, fetch the job description and apply the eligibility rules. Rejected postings are
   recorded so they are not reconsidered.
4. Tailor and compile a resume for each accepted posting until the daily quota is reached.
5. Regenerate the dashboard, the spreadsheet and the daily log.

State is stored as JSON under `output/data/`. The dashboard embeds its data at build time, so it opens
directly from disk without a server.

## Requirements

- Python 3.11 or later
- A LaTeX distribution providing `latexmk` (MacTeX on macOS; `texlive-latex-extra` and `latexmk` on Linux)
- Optional: `openpyxl` for the spreadsheet (`pip install -r requirements.txt`) and `pdfinfo` from
  poppler for faster page counting

## Installation

```sh
git clone https://github.com/Effervescebt/internship-autopilot.git
cd internship-autopilot
cp config.example.toml config.toml
cp profile.example.toml profile.toml
```

`config.toml` and `profile.toml` are listed in `.gitignore` so that personal data is not committed.

## Configuration

`config.toml` controls the search term, SimplifyJobs categories, daily quota, per-company limit, title
filters, eligibility rules, page limit and output paths. Each option is documented in
`config.example.toml`.

`profile.toml` holds the resume content: contact details, education, sections with entries and bullets,
and skill groups. The example file describes a fictional person and should be replaced entirely.
Guidelines for writing it:

- Set `core = true` on entries that should appear on every resume.
- Give each bullet the keywords a job description would use for that work.
- Keep bullets to one or two lines so the page can hold more material.

## Usage

```sh
python3 -m autopilot run      # run the daily pipeline
python3 -m autopilot build    # regenerate the dashboard and spreadsheet only
python3 -m autopilot status   # number of postings added today
python3 -m autopilot tailor "Machine Learning Intern" jd.txt out_dir   # tailor a single resume
```

Output for each posting is written to `output/applications/<date>/<index>_<company>_<title>/`, containing
`Resume.pdf`, `resume.tex` and the job description in `jd.txt`.

Open `output/Dashboard.html` in a browser to review postings. Status changes are stored in the browser;
the "Save statuses" button exports them to `autopilot-status.json` in the configured download folder,
and the next run imports them into the records and the spreadsheet.

## Scheduling

`scripts/run_daily.sh` runs the pipeline at most once per day and only after the hour given by
`RUN_HOUR` (default 10). It is designed to be triggered repeatedly; later triggers exit immediately once
the day's run has completed. It retries up to three times per day and keeps macOS awake during a run.

macOS (launchd):

1. Copy `scripts/com.example.internship-autopilot.plist` to `~/Library/LaunchAgents/` and replace
   `/PATH/TO/internship-autopilot` with the project path.
2. Run `chmod +x scripts/run_daily.sh`.
3. Load the agent: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.internship-autopilot.plist`
4. If the project is inside Desktop or Documents, grant Full Disk Access to `/bin/zsh` in
   System Settings, Privacy & Security; otherwise macOS blocks the scheduled run.

A Mac with its lid closed sleeps regardless of this setting; the run resumes when the machine wakes.

Linux (cron), checking every 30 minutes:

```
*/30 * * * * /path/to/internship-autopilot/scripts/run_daily.sh
```

## Extending

Additional sources can be added in `autopilot/sources.py` as functions returning candidate records with
the fields `id`, `source`, `company`, `title`, `location`, `url`, `posted` and `sponsorship`. Review each
site's terms of service before adding a source; several job boards, including LinkedIn, prohibit
automated collection, and this project does not include code that collects from them.

## Limitations

- Keyword scoring is a heuristic. Every generated resume should be reviewed before submission.
- Career sites that render descriptions with JavaScript cannot be read; resumes for those postings are
  tailored on the job title alone, and the notes state this.
- Eligibility rules are pattern-based and may miss unusual wording. Confirm eligibility on the posting.

## License

MIT. See [LICENSE](LICENSE).
