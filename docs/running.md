# Running and packaging FinGuard

## Local development

From the repository root, create/select a Python >=3.11 environment. Install the project with `.venv\Scripts\python.exe -m pip install -e ".[dev,app]"` on Windows, then run `.venv\Scripts\python.exe -m pytest -q`. Start the server with `.venv\Scripts\python.exe -m streamlit run streamlit_app.py`. Stop it with Ctrl+C. Do not commit `.venv`, caches, secrets, or personal financial data.

The included sample is hypothetical. English and Spanish use USD and English numeric separators consistently. Nothing requires paid APIs or bank accounts. The selected return is an assumption, not a forecast.

## Portable server deployment

No site has been deployed or published. A Python host needs the repository, Python >=3.11, and the dependencies from `requirements.txt` (which installs the local project's `app` extra). Run installation from the repository root:

```text
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
```

Configure the host to route its chosen port to Streamlit, preserve the `.streamlit/config.toml` file, and use its normal HTTPS/reverse-proxy setup. Port selection and service startup depend on the host. Run the development test suite before release. No credentials or environment secrets are required by this app.

For reproducible deployment, record resolved dependency versions in the target Python environment and validate them there. `pyproject.toml` specifies supported ranges rather than an environment lock file. A fresh requirements install and local headless server were tested with Python 3.14.7 on Windows. Chromium desktop and mobile-emulated layouts were reviewed; other operating systems and physical devices have not been certified. See `QA_PREPUBLICACION.md` for evidence and limits.

## Streamlit Community Cloud preparation

The repository must include `streamlit_app.py`, `finguard/`, `data/sample_profile.json`, `.streamlit/config.toml`, `requirements.txt`, and `pyproject.toml`. Exclude local virtual environments, downloaded QA browsers, caches, and secrets using `.gitignore`. The local `.[app]` requirement assumes installation from the repository root, which was tested in a fresh environment.

When publishing is authorized, select the GitHub repository and branch in Community Cloud, use `streamlit_app.py` as the entrypoint, and choose a Python version supported by the host and dependencies. The environment validated here is Python 3.14.7; if the host offers a different version, test that version before treating the remote deployment as validated. No app secrets are required. Recheck the initial metrics, both languages, all five tabs, and the financial disclaimers after deployment. This project has not yet been uploaded or deployed by this QA process.

Official references: [file organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization), [dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies), and [deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
