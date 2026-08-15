# UI

A small Streamlit front end for the SQL agent. It's a pure HTTP client — it
calls the API in [../app](../app) and renders the response; it does not
import the agent directly.

## Run

```bash
uv pip install -r requirements.txt --python ../.venv
streamlit run ui/app.py
```

(run from the project root; requires the API from [../app](../app) to be
running — defaults to `http://localhost:8000`, override with the `API_URL`
env var or the sidebar field)

Opens at `http://localhost:8501`. Enter a question, hit **Ask**, and it shows
the database picked, the generated SQL, the plain-language report, and the
chart if one was produced.
