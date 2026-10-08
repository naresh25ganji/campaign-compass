# Deploy Campaign Compass

The live app is https://campaign-compass.streamlit.app/. It was deployed on October 8, 2026 from the public repository https://github.com/naresh25ganji/campaign-compass, branch `main`, entry point `app.py`, using Python 3.12. No secrets are required.

Chrome smoke checks confirmed all six views, campaign investigation navigation, empty channel selections, filter reset, and a locked budget scenario. Both HTML briefs downloaded from the hosted app; the budget brief opened independently and retained the lock and scenario assumptions.

## Streamlit Community Cloud

1. Sign in at https://share.streamlit.io and handle account terms and GitHub access prompts.
2. Choose **Create app**, then deploy from an existing GitHub repository.
3. Repository: `naresh25ganji/campaign-compass`.
4. Branch: `main`.
5. Main file: `app.py`.
6. Choose Python **3.12** in advanced settings to match the tested environment.
7. Deploy and wait for the build logs to complete. No API keys or secrets are required.

Community Cloud may select `uv.lock` when installing dependencies; it is committed alongside the pinned `requirements.txt`. The app finds source tables relative to `app.py`.

After deployment, verify all six views, reset filters, click an investigation, change a budget lock, download both briefs, and open the downloaded files. Then add the confirmed live URL to the README and submission document. Do not submit localhost as the public app link.

Official guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app
