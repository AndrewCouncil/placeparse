import csv
import json
from pathlib import Path
import click
import requests
import rich
import time
import re
from bs4 import BeautifulSoup
from tqdm import tqdm

API_KEY = "AIzaSyAPSiEwVygrDfJjJGovyoYPjpwMzNlv7NA"
PROJECT_DIR = Path(__file__).parent
SAVED_PLACES_FILE = PROJECT_DIR / "Takeout" / "Saved" / "Want to go.csv"
OUT_DIR = PROJECT_DIR / "output"
OUT_JSON_DIR = OUT_DIR / "restaraunt_data"

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

    out_file = OUT_JSON_DIR / f"{title}.json"
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
        for i, row in tqdm(enumerate(rows[1:])):
            click.secho(f"\nQuerying row {i}...", fg="blue", italic=True)
            query_save_place(row)
            time.sleep(1)


def extract_emails_from_html(html: str) -> set[str]:
    emails = set()
    # find mailto: links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href^=mailto]"):
        href = a.get("href", "")
        addr = href.split(":", 1)[-1].split("?")[0]
        if EMAIL_RE.fullmatch(addr):
            emails.add(addr)
    # also run regex on the raw HTML just in case
    emails |= set(EMAIL_RE.findall(html))
    return emails


def get_out_files() -> list[Path]:
    return list(OUT_JSON_DIR.glob("*.json"))


@cli.command()
def get_emails() -> None:
    """Attempt to get the email address for each restaraunt and add to the json data"""
    for file in tqdm(get_out_files()):
        click.secho("\n" + file.name, fg="blue", italic=True)
        with file.open() as f:
            data = json.load(f)

        name = data.get("name", file.stem)
        click.secho(name, fg="blue", bold=True)
        if data.get("email") or data.get("emails"):
            click.secho(f"Email(s) already exists for {name}", fg="yellow")
            continue

        website = data.get("website")
        if website:
            click.secho(f"Website found: {website}")
        else:
            click.secho(f"No website found for {name}", fg="red")
            continue

        try:
            resp = requests.get(website, timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            click.secho(f"Error fetching website {website} for {name}", fg="red")
            continue

        emails = list(extract_emails_from_html(resp.text))
        if not emails:
            click.secho(f"No emails found for {name}", fg="yellow")
            continue
        click.secho("Email(s) found:\n", fg="green")
        rich.print(emails)

        data["emails"] = emails
        with file.open("w") as f:
            json.dump(data, f, indent=2)

def bad_email(email: str) -> bool:
    bad_email_domains = [
        "example.com",
        "test.com",
        "invalid.com"
        "wixpress.com"
        ".js"
    ]
    return any(
        email.endswith(domain) for domain in bad_email_domains
    )

@cli.command()
def contacts() -> None:
    csv_out_file = OUT_DIR / "restaraunt_contacts.csv"
    with csv_out_file.open("w", newline="") as csvfile:
        fieldnames = ["Name", "Address", "Phone", "Emails"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for file in get_out_files():
            with file.open() as f:
                data = json.load(f)

            name = data.get("name", file.stem)
            phone = data.get("formatted_phone_number", "")
            original_emails: list[str] = data.get("emails", [])
            emails = " ".join(
                email for email in original_emails if not bad_email(email)
            )

            # Extract plain text address from HTML
            address = ""
            if "adr_address" in data:
                soup = BeautifulSoup(data["adr_address"], "html.parser")
                address = soup.get_text().strip()

            writer.writerow(
                {
                    "Name": name,
                    "Address": address,
                    "Phone": phone,
                    "Emails": emails,
                }
            )

    click.secho(f"Contacts exported to {csv_out_file}", fg="green")


if __name__ == "__main__":
    cli()
