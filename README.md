# Interior Design Platform (CSIT314 Group Project)

An online platform that matches renovation customers with interior designers.
Built with **Python + Flask + SQLite**, following the **Boundary-Control-Entity (BCE)** design.

## 1. Setup (Windows, one time)

```bash
cd "SDM Codes"
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Create the database

**For the demo (recommended)** - creates the database and fills it with test data:

```bash
python scripts/generate_test_data.py
```

This creates about 130 accounts, 30 categories, 180 IDPs, 650 favourites, 6,000 IDP views,
40 reports, 3 estimation rules and 300 cost breakdowns, spread over the last 90 days.
Running it again wipes the database and recreates the same data (`--seed 7` gives different data).

**Empty database** - only the 5 user profiles, the demo accounts and a starter estimation rule:

```bash
python scripts/init_db.py
```

Both scripts create these demo accounts (all generated accounts also use `Password123!`):

| Username | Role | Password |
|---|---|---|
| admin | User Admin | Password123! |
| designer | Interior Designer | Password123! |
| customer | Customer | Password123! |
| pmanager | Platform Manager | Password123! |
| smanager | Sales Manager | Password123! |

## 3. Run the app

```bash
python run.py
```

Open http://127.0.0.1:5000 and log in. Press Ctrl+C to stop.
Next time you only need: `venv\Scripts\activate` then `python run.py`.
Visitors can browse projects without logging in; customers can sign up from the top bar.

## 4. Run the tests

```bash
python -m pytest            # all tests (about 10 seconds)
python -m pytest -v         # list every test by name
python -m pytest tests/test_us47_create_estimation_rule.py -v   # one story
```

## 5. User stories

| # | Story | Log in as | Menu / page |
|---|---|---|---|
| - | Browse / search projects | nobody (public) | Browse Projects (/projects) |
| - | Project page: photos, details, cost estimate, cost breakdown by property type | nobody (public) | click any project |
| - | Sign up (customers) | nobody | Sign Up (/signup) |
| - | Choose interests (shown on home page) | customer | after sign-up, or My Interests |
| - | Save / remove favourites | customer | button on a project page |
| - | Login / Logout | anyone | /login |
| - | Edit user account (incl. password reset), reactivate account | admin | Accounts & Activity Log > Edit / Reactivate |
| - | Manage user profiles (create, edit, suspend) | admin | User Profiles |
| - | Company information + public designer page | designer | Company Information; /designers/&lt;id&gt; |
| - | Manage categories (create, edit, status, delete unused, see requests) | pmanager | Categories |
| - | Platform reports (daily / weekly / monthly + CSV) | pmanager | Reports |
| #1 | Create User Account | admin | Create User Account |
| #7 | View Account Activity Log | admin | View Activity Log |
| #11 | Manage Project Categories | designer | Manage Portfolio > Edit Categories |
| #13 | Manage Portfolio | designer | Manage Portfolio |
| #27 | Compare Favourite IDPs | customer | My Favourites |
| #29 | Generate Cost Breakdown | customer | Cost Breakdown |
| #38 | Manage Reports on Inappropriate IDPs | pmanager | Manage Reports |
| #40 | Category Health Report | pmanager | Category Health |
| #47 | Create Cost Estimation Rules | smanager | Estimation Rules |
| #50 | Export Sales Report | smanager | Sales Reports |

How the stories connect:
- **#47 -> #29 -> #50**: the Sales Manager's active rule sets the prices and multipliers in the customer's
  cost breakdown; saved breakdowns are counted in the sales report.
- **#11 / interests -> customer home page**: a project's categories and the customer's chosen interests decide
  what appears under "Projects you might like".
- **#13 cost breakdown -> project page**: the designer enters unit rates per project (Edit / Add Project); visitors
  can switch the property type and the breakdown is scaled by the property multiplier from #47's active rule
  (relative to the project's own property type). The project's total cost is the breakdown's subtotal.
- **Project page views and favourites -> #40, #50 and the designer's Views / Shortlisted counts.**
- **#13 / #38**: archived (designer) or hidden (Platform Manager) projects disappear from recommendations,
  favourites comparison and category health.

## 6. Required functions (project specification)

| Spec requirement | Implemented functions | Status |
|---|---|---|
| 1. Manage user accounts and profiles | Login/logout and role access; create account (#1); customer sign-up; list/search accounts and activity log (#7); edit account and reset password; suspend / reactivate account; create, edit and suspend user profiles | Done |
| 2. ID manages company information | Company information page (name, UEN, address, phone, email, website, description), shown on project pages and a public designer page | Done |
| 3. ID manages portfolio of IDPs | Add project, edit details + photos + cost breakdown, archive / restore / delete (#13), categories (#11) | Done |
| 4. Customer searches, views, saves IDPs | Browse and search (public), project page, save/remove favourites, favourites list, compare (#27), cost breakdown (#29) | Done |
| 5. ID tracks interest in IDPs | Views and times shortlisted on every Manage Portfolio card | Done |
| 6. Platform Manager manages categories and gets reports | Create / edit / delete categories and see designers' requests; daily / weekly / monthly platform report with CSV; category health (#40); reported IDPs (#38) | Done |
| Test data (about 100 records per type) | `scripts/generate_test_data.py` | Done |

## 7. Project structure (BCE)

```
app/
  boundary/    <<boundary>> page classes + Flask routes (one file per user story)
  control/     <<control>> controller classes (one per user story)
  entity/      <<entity>> data classes, one per data type (shared by all stories)
  templates/   HTML pages
  static/      CSS (uploaded IDP photos go to static/uploads/)
  constants.py shared roles, status values, renovation items and menus
  schema.sql   database tables
  db.py        database connection
scripts/       init_db.py (empty database), generate_test_data.py (demo data)
docs/screenshots/  a screenshot of every story (for the report), plus a sample sales report CSV
tests/         pytest unit tests (one file per user story)
.github/       GitHub Actions CI/CD workflow
render.yaml    Render deployment settings
run.py         starts the web app
```

Class and method names follow the class and sequence diagrams in the report
(e.g. `CreateEstimationRuleController.createEstimationRule()`), so the code matches the design.

**Which code implements which user story:** see [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md) (summary per story).
**Where each feature is and how it flows (file + line numbers, call order):** see
[`docs/CODE_WALKTHROUGH.md`](docs/CODE_WALKTHROUGH.md).
Both are generated from the code, so after changing code run:

```bash
python scripts/traceability.py
python scripts/walkthrough.py
```

## 8. GitHub

Create an **empty** repository on GitHub (no README), then in this folder:

```bash
git init
git add .
git commit -m "Initial version: 10 user stories with tests"
git branch -M main
git remote add origin https://github.com/<your-account>/<repo-name>.git
git push -u origin main
```

Suggested team workflow: one branch per user story (e.g. `feature/us29-cost-breakdown`), open a
pull request, let the CI tests pass and another member review it, then merge into `main`.

## 9. CI/CD

- **CI** - `.github/workflows/ci.yml` runs on every push and pull request: installs the requirements,
  runs all unit tests on Python 3.10 and 3.12, and checks the test data generator. Results are in the
  repository's **Actions** tab (screenshots of passing/failing runs are good report evidence).
- **CD** - when the tests pass on `main`, the workflow deploys the app to Render:
  1. Sign up at https://render.com with your GitHub account.
  2. New > Blueprint > pick this repository (it reads `render.yaml`) > Apply.
  3. In Render, open the service > Settings > Deploy Hook > copy the URL.
  4. In GitHub, Settings > Secrets and variables > Actions > New repository secret:
     name `RENDER_DEPLOY_HOOK_URL`, value = the URL.
  5. Push to `main`. After the tests pass, the deploy job starts the deployment and the site is live
     at the Render URL with fresh test data.

## 10. Notes

- Emails (login credentials in #1, warnings/outcomes in #38, category requests in #11) are saved to the
  `notification` table instead of being sent, so no mail server is needed.
- Passwords are stored as hashes. Usernames are not case-sensitive; passwords are.
- The database file can be moved with the environment variable `SDM_DB_PATH`.
