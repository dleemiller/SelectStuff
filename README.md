# SelectStuff

Note: This is not in an especially user-friendly state. As of yet, it's very incomplete and buggy.
The architecture may change significantly, and is under active development.

This project enables you to *select stuff* in your browser, and then:
- paste it to a locally hosted server endpoint (FastAPI)
- process it using an "application" (eg "news" processes metadata from an article)
- then provides a search interface to find what you've saved

This platform is intended to be used with language models in order to provide
a quality search and retrieval experience.


## Startup

Moving parts:
- FastAPI server (uvicorn): interacts with the database and LLMs
- streamlit search UI: search interface for API
- duckdb (->moving to sqlite?) database for storage and retrieval
- browser extensions (right now just chrome)

Install the dependencies in `pyproject.toml`.

## Export the list of ENABLED_APPS
```bash
$ export ENABLED_APPS=news
```

## FastAPI server

```bash
$ uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Streamlit Server

```bash
$ cd search_app
$ streamlit run main.py --server.address 0.0.0.0
```

## Extensions

Open chromium, click on the "puzzle piece" extension button:

```
> manage extensions
-> Load Unpacked (developer toggle on)
--> Select extension folder

> Click puzzle piece icon again
-> Click three dots next to extension
--> Options (set IP of fast api server)
```

## To generate requirements.txt
```bash
$ poetry self add poetry-plugin-export
$ poetry export -f requirements.txt --output requirements.txt --without-hashes --all-groups
```
