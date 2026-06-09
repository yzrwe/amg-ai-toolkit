# amg-ai-toolkit

A working demo of AI-assisted workflows for a pension **Asset Management
Group** — built around the day-to-day of a multi-asset retirement plan
(public equities, fixed income, hedge funds, private markets) managed by
external managers and reported through a custodian.

Each module maps to a real AMG task: data QA before reporting, custodian
vs. manager performance reconciliation, intake of manager communications
(capital calls, letters, amendments), portfolio positioning monitoring, and
the monthly report itself. Built end-to-end with an AI coding assistant
(Claude) as the primary development tool. All data is synthetic.

## What's in here

```
amg-ai-toolkit/
├── data/
│   ├── generate_dataset.py      # Seeded synthetic plan: 14 managers, 24 months,
│   │                            #   $12B illustrative DB plan — with 4 injected
│   │                            #   data issues for the controls to catch
│   └── portfolio_monthly.csv
├── qa/data_quality_checks.py    # Pipeline-gating QA controls (exits non-zero on failure)
├── recon/reconcile_performance.py  # Custodian vs manager recon w/ tolerance bands (5/25 bps)
├── skills/manager-communications/
│   ├── skill.yaml               # Structured AI skill: capital calls, distributions,
│   └── SKILL.md                 #   letters, amendments — extraction rules, validations,
│                                #   fraud-check flags, human-review gates
├── app.py                       # Streamlit dashboard: allocation vs target, drift,
│                                #   NAV trend, recon status
└── exports/build_monthly_report.py  # openpyxl 3-tab formatted monthly report
```

## Run it

```bash
pip install -r requirements.txt
python data/generate_dataset.py          # regenerate the dataset
python qa/data_quality_checks.py         # fails: catches the 4 injected issues
python recon/reconcile_performance.py --month 2026-03   # catches the 85bps break
python exports/build_monthly_report.py   # writes the 3-tab Excel report
streamlit run app.py                     # portfolio monitor
```

## Design notes

- **Controls are testable by construction.** The dataset generator plants a
  duplicate row, a missing return, an impossible NAV, and an 85bps
  custodian/manager break — so the QA and recon modules demonstrably catch
  what they claim to catch.
- **AI where it helps, gates where it matters.** The manager-communications
  skill drafts structured summaries and action checklists, but every output
  is marked `DRAFT — pending human review`, extracted figures must appear
  verbatim in the source, and changed wire instructions always trigger a
  fraud-check flag (the #1 capital-call fraud vector). AI compresses review
  time; it doesn't replace the reviewer.
- **Alternatives reported realistically.** Hedge funds and private markets
  carry explicit reporting-lag metadata (1–3 months), handled as a known
  attribute rather than treated as missing data.

---

*Regis Yizerwe — yizerwer@gmail.com*
