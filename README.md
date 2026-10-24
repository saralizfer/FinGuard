# FinGuard

Financial Resilience & Wealth Readiness Simulator. Independent educational portfolio project using hypothetical data. Simulations are not predictions or personalized investment recommendations.

## Current stage

The application has five bilingual tabs sharing one financial profile:

1. **My financial profile:** monthly income, spending, credit card balance/APR, minimum and optional extra debt payments, savings, contributions, and a selected emergency target.
2. **Financial assessment:** the six validated indicators, a readable horizontal waterfall, emergency-target donut/progress, neutral explanations, and the existing spending explorer.
3. **Emergency simulator:** medical expense, vehicle repair, temporary total income loss, reduced income, or rising essential expenses. Includes a monthly ledger, savings/debt timeline, borrowing, interest paid versus accrued, depletion, and recovery under explicit assumptions.
4. **Recovery strategies:** savings-first, debt-first with a selected reserve, and balanced recovery; consistent initial conditions and allocation caps; charts and 12/24-month comparisons.
5. **Wealth readiness:** hypothetical goals, contribution affordability, contributions-only and uncertain-return projections, and the trade-off of pausing contributions.

Switching tabs or languages preserves inputs. The introduction remains above the tabs. The profile reset affects profile values only; selected scenarios and projection controls remain unchanged. Results are deterministic and update when inputs change. Small pure financial computations are cached with bounded entries and session scope; navigating does not change financial assumptions or execute external actions. Widget values persist for the current Streamlit session; there is no database, authentication, bank connection, or durable personal-data storage. The simulator explicitly explains that minimum payments are user-entered fixed amounts, including on new borrowing.

The dashboard greets the current viewer as “Welcome, Carlos” / “Bienvenido, Carlos” using fictional demonstration defaults. The display identity is separate from the financial `Profile`: `UserContext` in `finguard/user_context.py` is stored in `st.session_state["user_context"]`. A future profile editor can supply another display name without changing any financial formulas. There is no sign-in or claim of an authenticated private account. Educational scope, data handling, and financial limitations are accessible in the collapsed **About FinGuard** section in the sidebar rather than a persistent footer.

Release QA evidence is documented in `docs/QA_PREPUBLICACION.md`: fresh installation, 170 passing tests, dependency and source scans, and real Chromium desktop/mobile-emulation checks across all five tabs and both languages. Local QA does not certify Streamlit Cloud deployment, all browsers, physical devices, or complete accessibility.

The local feedback update adds deterministic interpretations and educational next steps in the assessment, emergency, recovery, and wealth tabs. It uses the current model outputs, changes when inputs change, and supports English and Spanish. It distinguishes an ordinary budget deficit from an unfunded savings transfer, describes liquidity/interest trade-offs, and prioritizes contribution affordability over a projected goal being reached. No external AI service, new scoring system, or investment recommendation is used. `finguard/feedback.py` contains the rules and `feedback_copy.py` contains bilingual copy. Updating local files does not update the hosted app until the changed files are committed to its GitHub branch.

The spending explorer applies a hypothetical percentage reduction to discretionary expenses while keeping income, essentials, debt payments, and savings contributions fixed. It reuses the assessment engine and does not overwrite the original profile. For the sample, a 50% reduction frees $250 monthly and changes available cash after saving from $950 to $1,200. It does not model debt interest or recovery time. The emergency ring displays savings up to the selected target; excess savings are described separately. A zero target displays an explanation instead of a percentage.

The visual theme lives in `.streamlit/config.toml` and uses system fonts, with no external font downloads or custom CSS. If the app was already running when the theme file was added, restart the Streamlit process and refresh the browser to load it.

## Development stages

The initial two-day scope established and tested the assessment engine before building the interface. The expanded product adds tested monthly simulation, recovery comparisons, and independent wealth projections. These are implemented educational models, not independently certified financial tools.

Scope limits: USD, one aggregate credit card balance and APR, one emergency scenario at a time, a fixed baseline savings target, and up to 120 simulation months. Investment projections use constant hypothetical rates for up to 50 years. Debt uses monthly APR/12 accrual; investment assumptions use an effective annual rate converted to a monthly rate. See `docs/model.md` for all formulas, cash-flow identities, timing, and limitations.

## Project structure

```text
streamlit_app.py           # Five tabs, shared profile, persistent introduction
finguard/
    __init__.py
    assessment.py         # Implemented assessment formulas
    simulation.py         # Monthly transaction engine and ledger
    recovery.py           # Comparable recovery paths
    wealth.py             # Goal projection calculations
    translations.py       # Central bilingual TEXT interface
    product_copy.py       # Additional bilingual product copy merged into TEXT
    ui_common.py          # Currency, wrapping cards, chart helpers
    ui_assessment.py      # Existing assessment dashboard
    ui_simulation.py      # Emergency and recovery controls and charts
    ui_wealth.py          # Goal planning and independent projections
data/
    sample_profile.json
docs/
    model.md
tests/
    test_assessment.py
    test_app.py
    test_simulation.py
    test_translations.py
pyproject.toml
```

## Local setup in Visual Studio Code

Open this folder with **File > Open Folder**. Install Microsoft's Python extension and open **Terminal > New Terminal** (PowerShell).

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev,app]"
.venv\Scripts\python.exe -m pytest
```

Choose **Python: Select Interpreter** from the Command Palette and select `.venv\Scripts\python.exe`. Calling the interpreter directly avoids PowerShell activation-policy changes.

Launch the interface:

```powershell
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Open the local URL printed in the terminal. Stop the server with **Ctrl+C**.

### Verify the assessment

The default sample should show $1,350.00 cash flow before saving, $950.00 available after saving, 2.09 months of coverage, a $6,450.00 target, a $1,950.00 shortfall, and a 3.75% debt-payment ratio. Change income to $5,000: cash flow should become $2,350.00. Switch to Spanish: inputs and results should persist. Reset the sample to restore the initial values.

For a manual simulation check, enter income 1,000; essentials 600; discretionary 100; savings 500; debt 1,000; APR 24%; required payment 100; planned savings 100; extra debt payment 50; target 3 months. Select a medical shock of 1,000. The ledger's first month must show interest 20, cash flow -800, savings withdrawn 500, borrowing 300, closing savings 0, and closing debt 1,220.

In Wealth readiness, initial amount 1,000, monthly contribution 100, one year, and 0% return should give a value of 2,200; pausing three initial contributions produces a 1,900 comparison path.

The automated suite checks the assessment, monthly source/use and stock identities, interest attribution and timing, borrowing, debt payoff, recovery allocations, reserves, projection timing, invalid inputs, and bilingual UI state. AppTest runs without a browser; browser appearance and responsive layout still require visual review. Metric titles now use wrapping Markdown headings; currency prose escapes dollar signs to avoid unintended LaTeX rendering.

Review `docs/model.md` alongside `finguard/assessment.py` and `tests/test_assessment.py` to connect each formula with its implementation and expected result.

On this workstation, `.venv` has already been created. If `python` opens the Microsoft Store, select the installed Python interpreter in VS Code or use its full executable path to create the environment. Use `.venv\Scripts\python.exe` for subsequent commands.
