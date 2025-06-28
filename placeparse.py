import csv
import json
from pathlib import Path
import click
import requests
import rich
import time
import re

API_KEY = "AIzaSyAPSiEwVygrDfJjJGovyoYPjpwMzNlv7NA"
PROJECT_DIR = Path(__file__).parent
SAVED_PLACES_FILE = PROJECT_DIR / "Takeout" / "Saved" / "Want to go.csv"
OUT_DIR = PROJECT_DIR / "output"
ALNUM_REGEX = re.compile(r"[^a-zA-Z0-9_-]")


def query_save_place(row: dict[str, str]):
    original_title = row.get("Title", "")
    title = ALNUM_REGEX.sub("", original_title.lower().replace(" ", "_"))
    click.secho(title, fg="blue", bold=True)

    url = row.get("URL")
    if not url:
        click.secho("No URL found", fg="red", err=True)
        return
    click.secho(url, fg="yellow")

    hex_cid = url.split(":")[-1]
    cid = int(hex_cid, 16)
    click.echo(cid)

    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={"cid": cid, "key": API_KEY},
        )
        resp.raise_for_status()
        result = resp.json()["result"]
    except Exception as e:
        click.secho(f"Error for id: {cid}, title:{title}\n{e}", fg="red", err=True)
        return
    rich.print(result)

    row["result"] = result

    out_file = OUT_DIR / f"{title}.json"
    with out_file.open("w") as f:
        json.dump(result, f, indent=2)


def main() -> None:
    with SAVED_PLACES_FILE.open() as f:
        rows = list(csv.DictReader(f))
        for i, row in enumerate(rows[1:]):
            click.secho(f"\nQuerying row {i}...", fg="blue", italic=True)
            query_save_place(row)
            time.sleep(1)


if __name__ == "__main__":
    main()
