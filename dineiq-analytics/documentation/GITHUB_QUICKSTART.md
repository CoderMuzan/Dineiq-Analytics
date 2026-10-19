# GitHub quick start (solo, about 10 minutes the first time)

**Why:** the SRS (section 1.8 and deliverable 12) requires a *public* repository with meaningful commits on **each of the five
competition days**. Evaluators use the commit history to check that the work is genuinely yours. It is not a data-science
habit you must keep after the competition - it is simply part of the marking here.

## One-time setup
1. Install Git (https://git-scm.com) and make a free account at github.com.
2. On github.com click **New repository**, name it `dineiq-analytics`, choose **Public**, do not add a README (you already have files).
3. In a terminal inside your project folder:
```
git init
git add .
git commit -m "Phase 1: dataset generator, ER diagram, data dictionary"
git branch -M main
git remote add origin https://github.com/CoderMuzan/dineiq-analytics.git
git push -u origin main
```
(If GitHub asks for a password, create a Personal Access Token under Settings > Developer settings, and paste it as the password.)

## Every day of the competition (and any day you work)
```
git add .
git commit -m "Day 2: Spark cleaning rules + tests"
git push
```
Make 2-4 commits a day with honest messages describing what changed. Do not make one giant commit at the end.

## What NOT to upload
Big data folders are ignored by `.gitignore`. The SRS allows external storage for large datasets: upload
`parquet_data/` and `clean_data/` to Google Drive / Hugging Face Datasets / Kaggle and put the public link in your README.
Never commit passwords or tokens.

## Also keep (SRS 1.8)
- A development log (`documentation/DEV_LOG.md`): date, what you did, problems found, Spark failures, fixes, tests run.
- `AI_USAGE.md` kept up to date.
