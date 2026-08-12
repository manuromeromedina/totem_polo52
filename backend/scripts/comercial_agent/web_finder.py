"""
Ubicación del sitio/red social pública de una empresa, sin usar ninguna API
de búsqueda paga:

1. Si el excel ya trae una URL, se usa esa.
2. Si no, se prueban dominios candidatos armados con el nombre de la empresa
   (heurística: nombre-slug.com.ar / .com).
3. Si nada de eso responde, se busca en DuckDuckGo (endpoint HTML, sin API
   key) y se toma el primer resultado que parezca un sitio propio o, en su
   defecto, un perfil de Instagram/Facebook.

Es deliberadamente best-effort: para una empresa chica sin presencia web
clara, puede no encontrar nada, y eso queda reflejado en el CSV de revisión
en vez de inventarse un resultado.
"""
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (compatible; Polo52ComercialAgent/1.0; "
    "+https://totem.aeye.com.ar; uso academico para completar base propia)"
)
REQUEST_TIMEOUT = 8
_SOCIAL_DOMAINS = ("instagram.com", "facebook.com", "linkedin.com")
_IGNORE_DOMAINS = (
    "google.com", "bing.com", "duckduckgo.com", "wikipedia.org",
    "paginasamarillas.com.ar", "guiaindustrial.com.ar", "mercadolibre.com.ar",
    "youtube.com", "maps.app.goo.gl",
)


@dataclass
class WebResult:
    url: str
    source: str  # "excel" | "heuristica" | "busqueda"


def _slugify(nombre: str) -> str:
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn"
    )
    normalized = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    return normalized


def _normalize_excel_url(raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw or raw.lower() in ("no tiene", "no", "n/a", "-"):
        return None
    if not raw.startswith(("http://", "https://")):
        raw = f"https://{raw}"
    return raw


def _url_responds(url: str) -> bool:
    try:
        resp = requests.head(
            url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True
        )
        if resp.status_code >= 400:
            resp = requests.get(
                url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}, allow_redirects=True
            )
        return resp.status_code < 400
    except requests.RequestException:
        return False


def _try_heuristic_domains(nombre: str) -> Optional[str]:
    slug = _slugify(nombre)
    if not slug:
        return None
    for domain in (f"https://www.{slug}.com.ar", f"https://{slug}.com.ar", f"https://www.{slug}.com"):
        if _url_responds(domain):
            return domain
    return None


def _duckduckgo_search(query: str) -> List[str]:
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    links = []
    for a in soup.select("a.result__a"):
        href = a.get("href")
        if href:
            links.append(href)
    return links


def _pick_best_link(links: List[str]) -> Optional[WebResult]:
    social_fallback = None
    for link in links:
        if any(bad in link for bad in _IGNORE_DOMAINS):
            continue
        if any(social in link for social in _SOCIAL_DOMAINS):
            if social_fallback is None:
                social_fallback = link
            continue
        return WebResult(url=link, source="busqueda")
    if social_fallback:
        return WebResult(url=social_fallback, source="busqueda")
    return None


def find_company_url(
    nombre: str, rubro: Optional[str] = None, excel_url: Optional[str] = None
) -> Optional[WebResult]:
    if excel_url:
        normalized = _normalize_excel_url(excel_url)
        if normalized:
            return WebResult(url=normalized, source="excel")

    heuristic = _try_heuristic_domains(nombre)
    if heuristic:
        return WebResult(url=heuristic, source="heuristica")

    query = f'"{nombre}" Polo Industrial 52 Córdoba'
    if rubro:
        query += f" {rubro}"
    links = _duckduckgo_search(query)
    result = _pick_best_link(links)
    time.sleep(1.5)  # cortesia con DuckDuckGo antes de la siguiente empresa
    return result
