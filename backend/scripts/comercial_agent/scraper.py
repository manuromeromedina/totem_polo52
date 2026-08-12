"""Descarga y limpieza del texto visible de la web de una empresa."""
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from web_finder import USER_AGENT, REQUEST_TIMEOUT

MAX_CHARS = 6000
_CONTACT_LINK_HINTS = ("contacto", "nosotros", "about", "quienes-somos", "empresa")


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return " ".join(text.split())


def _find_contact_link(html: str, base_url: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(hint in href for hint in _CONTACT_LINK_HINTS):
            return urljoin(base_url, a["href"])
    return None


def scrape_text(url: str) -> Optional[str]:
    """Devuelve el texto visible de la home (+ una subpágina de contacto si existe), truncado."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException:
        return None

    home_text = _extract_text(resp.text)
    combined = home_text

    contact_url = _find_contact_link(resp.text, url)
    if contact_url and contact_url != url:
        try:
            contact_resp = requests.get(
                contact_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}
            )
            if contact_resp.ok:
                combined += " " + _extract_text(contact_resp.text)
        except requests.RequestException:
            pass

    combined = combined.strip()
    if not combined:
        return None
    return combined[:MAX_CHARS]
