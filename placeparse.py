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

ALPHANUM_RE = re.compile(r"[^a-zA-Z0-9_-]")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE)


def query_save_place(row: dict[str, str]):
    original_title = row.get("Title", "")
    title = ALPHANUM_RE.sub("", original_title.lower().replace(" ", "_"))
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


@click.group()
def cli():
    """Script for various parsing on saved google maps lists"""


@cli.command()
def query_list() -> None:
    """Query the list of saved places' google maps data and save as json"""
    with SAVED_PLACES_FILE.open() as f:
        rows = list(csv.DictReader(f))
        for i, row in enumerate(rows[1:]):
            click.secho(f"\nQuerying row {i}...", fg="blue", italic=True)
            query_save_place(row)
            time.sleep(1)


@cli.command()
def emails() -> None:
    """Attempt to get the email address for each restaraunt and add to the json data"""
    for file in OUT_DIR.glob("*.json"):
        click.secho(file.name, fg="blue", italic=True)
        with file.open() as f:
            data = json.load(f)

        name = data.get("name")
        if data.get("email"):
            click.secho(f"Email already exists for {name}", fg="yellow")
            continue

        # try:
        #     resp = requests.get(
        #         "https://maps.googleapis.com/maps/api/place/details/json",
        #         params={"cid": data["cid"], "key": API_KEY},
        #     )
        #     resp.raise_for_status()
        #     result = resp.json()["result"]
        # except Exception as e:
        #     click.secho(f"Error for id: {data['cid']}, title:{data['name']}\n{e}", fg="red", err=True)
        #     continue
        # email = result.get("email")
        # if email:
        #     data["email"] = email
        #     with file.open("w") as f:
        #         json.dump(data, f, indent=2)


if __name__ == "__main__":
    cli()
