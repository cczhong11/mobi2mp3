"""Read the Volcengine billing-account balance used by the Volc TTS workflow.

The TTS ``access_key`` used by the streaming endpoint is an application token;
it cannot query billing.  This command intentionally uses separate Volcengine
IAM access keys supplied at runtime, so neither kind of credential is stored in
the repository.
"""

import base64
import os
from typing import Optional

import click
import requests


ENDPOINT = "https://open.volcengineapi.com"


def _basic_auth(access_key_id: str, secret_access_key: str) -> str:
    """Return the Basic credential format documented for QueryBalanceAcct."""
    raw = f"{access_key_id}:{secret_access_key}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def query_balance(access_key_id: str, secret_access_key: str, timeout: int) -> dict:
    response = requests.get(
        ENDPOINT,
        params={"Action": "QueryBalanceAcct", "Version": "2022-01-01"},
        headers={"Authorization": _basic_auth(access_key_id, secret_access_key)},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    error = payload.get("ResponseMetadata", {}).get("Error")
    if error:
        raise click.ClickException(f"Volcengine returned {error.get('Code')}: {error.get('Message')}")
    return payload.get("Result", {})


@click.command()
@click.option("--access-key-id", envvar="VOLC_BILLING_ACCESS_KEY_ID", help="Volcengine IAM access-key ID.")
@click.option("--secret-access-key", envvar="VOLC_BILLING_SECRET_ACCESS_KEY", help="Volcengine IAM secret access key.")
@click.option("--timeout", default=20, show_default=True, type=int)
@click.option("--json-output", is_flag=True, help="Print the unmodified API result as JSON.")
def main(
    access_key_id: Optional[str], secret_access_key: Optional[str], timeout: int, json_output: bool
) -> None:
    """Show available Volcengine account balance (not a TTS token counter)."""
    if not access_key_id or not secret_access_key:
        raise click.UsageError(
            "Billing IAM credentials are required. Set VOLC_BILLING_ACCESS_KEY_ID and "
            "VOLC_BILLING_SECRET_ACCESS_KEY through a secret manager or pass the options. "
            "Do not use the Volc TTS application access_key here."
        )

    result = query_balance(access_key_id, secret_access_key, timeout)
    if json_output:
        import json

        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    click.echo("Volcengine billing account")
    for api_name, label in (
        ("AvailableBalance", "Available balance"),
        ("CashBalance", "Cash balance"),
        ("CreditLimit", "Credit limit"),
        ("FreezeAmount", "Frozen amount"),
        ("ArrearsBalance", "Arrears"),
    ):
        if api_name in result:
            click.echo(f"{label}: {result[api_name]}")


if __name__ == "__main__":
    main()
