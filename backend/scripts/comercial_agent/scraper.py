"""Descarga y limpieza del texto visible de la web de una empresa."""
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from web_finder import USER_AGENT, REQUEST_TIMEOUT

MAX_CHARS = 9000
# Se buscan por separado: una pagina "quienes somos" (rica en descripcion de
# la empresa) y una de contacto (rica en telefono/correo/direccion). Asi no
# se pierde una por la otra si el sitio tiene las dos.
_ABOUT_LINK_HINTS = ("nosotros", "about", "quienes-somos", "quienes_somos", "empresa", "historia")
_CONTACT_LINK_HINTS = ("contacto", "contact")


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return " ".join(text.split())


def _find_link(html: str, base_url: str, hints: tuple) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(hint in href for hint in hints):
            return urljoin(base_url, a["href"])
    return None


def _fetch(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.ok:
            return _extract_text(resp.text)
    except requests.RequestException:
        pass
    return None


def scrape_text(url: str) -> Optional[str]:
    """
    Devuelve el texto visible combinado de la home + una subpágina "quienes
    somos"/historia (si existe) + una subpágina de contacto (si existe),
    truncado. Más contenido = descripciones más completas en extractor.py.
    """
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
    except requests.RequestException:
        return None

    home_html = resp.text
    parts = [_extract_text(home_html)]

    about_url = _find_link(home_html, url, _ABOUT_LINK_HINTS)
    if about_url and about_url != url:
        about_text = _fetch(about_url)
        if about_text:
            parts.append(about_text)

    contact_url = _find_link(home_html, url, _CONTACT_LINK_HINTS)
    if contact_url and contact_url != url and contact_url != about_url:
        contact_text = _fetch(contact_url)
        if contact_text:
            parts.append(contact_text)

    combined = " ".join(p for p in parts if p).strip()
    if not combined:
        return None
    return combined[:MAX_CHARS]
