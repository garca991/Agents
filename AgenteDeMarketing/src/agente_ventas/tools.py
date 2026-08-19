"""
Tools for Web Searching and Web Scraping using LightPanda (via Playwright CDP).
"""

import logging
import os
import re
import time
import urllib.parse
import urllib.request

from dotenv import load_dotenv
from langchain_core.tools import tool
from playwright.sync_api import sync_playwright

load_dotenv()

# Logger for this module
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# --- Configuración desde variables de entorno ---
NAV_TIMEOUT_MS = int(os.environ.get("LIGHTPANDA_NAV_TIMEOUT_MS", "60000"))
HTTP_TIMEOUT_S = int(os.environ.get("LIGHTPANDA_HTTP_TIMEOUT_S", "30"))
MAX_RETRIES = int(os.environ.get("LIGHTPANDA_MAX_RETRIES", "3"))

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

# Default fallback CDP endpoints (tried in order after any user-configured URL)
_DEFAULT_CDP_CANDIDATES = [
    "ws://127.0.0.1:9222",
    "ws://localhost:9222",
    "ws://host.docker.internal:9222",
    "ws://172.17.0.1:9222",
]

# Indicadores de que DDG devolvió una página de detección de bots
_BOT_DETECTION_MARKERS = [
    "anomaly",
    "bot",
    "robot",
    "captcha",
    "blocked",
    "access denied",
    "cloudflare",
]


def _get_cdp_candidates() -> list[str]:
    """Devuelve una lista de URLs de CDP probables, priorizando la configurada por el usuario."""
    configured = []
    raw_value = os.environ.get("LIGHTPANDA_CDP_URL") or os.environ.get("LIGHTPANDA_CDP_URLS", "")
    if raw_value:
        configured = [item.strip() for item in raw_value.split(",") if item.strip()]

    # Siempre incluir los fallbacks por defecto después de las configuradas
    candidates = list(configured) + list(_DEFAULT_CDP_CANDIDATES)

    if os.path.exists("/.dockerenv") or os.environ.get("IN_DOCKER") == "1":
        # Running in Docker: prefer host.docker.internal but keep loopback candidates available
        if "ws://host.docker.internal:9222" in candidates:
            candidates.remove("ws://host.docker.internal:9222")
        candidates.insert(0, "ws://host.docker.internal:9222")

    # dedupe while preserving order
    seen = []
    for candidate in candidates:
        if candidate not in seen:
            seen.append(candidate)
    return seen


def _connect_to_lightpanda():
    """
    Conecta a LightPanda usando la URL de CDP directamente.

    LightPanda expone el CDP (Chrome DevTools Protocol) sobre un WebSocket
    en ``ws://host:9222``. A diferencia de Chrome/Chromium, LightPanda
    **no** implementa los endpoints HTTP de descubrimiento (``/json/version``,
    ``/json/list``), por lo que debemos conectar directamente con la URL
    ``ws://`` configurada o con los candidatos por defecto.
    """
    last_error = None
    candidates = _get_cdp_candidates()
    logger.debug("CDP discovery candidates: %s", candidates)
    for cdp_url in candidates:
        playwright = None
        try:
            logger.info("Conectando Playwright a LightPanda en %s", cdp_url)
            playwright = sync_playwright().start()
            browser = playwright.chromium.connect_over_cdp(cdp_url)
            logger.info("Conectado a LightPanda (cdp_url=%s)", cdp_url)
            return playwright, browser, cdp_url

        except Exception as exc:
            last_error = exc
            logger.warning("Fallo al conectar en %s: %s", cdp_url, exc)
            try:
                if playwright is not None:
                    playwright.stop()
            except Exception:
                pass

    raise RuntimeError(
        f"No se pudo conectar a LightPanda. Intenté: {candidates}. Último error: {last_error}"
    )


def _http_get(url: str, headers: dict | None = None, timeout_s: int = HTTP_TIMEOUT_S) -> str:
    """Realiza una petición HTTP simple y devuelve el HTML (sin ejecutar JS)."""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        return response.read().decode("utf-8", errors="replace")


def _fetch_with_local_browser(url: str, headers: dict | None = None, timeout_ms: int = NAV_TIMEOUT_MS) -> str:
    """Intenta cargar una URL con un navegador local si LightPanda no puede completar la navegación."""
    playwright = None
    browser = None
    try:
        playwright = sync_playwright().start()
        for browser_type in (playwright.chromium, playwright.firefox, playwright.webkit):
            try:
                browser = browser_type.launch(headless=True)
                break
            except Exception as exc:
                logger.debug("Browser %s no disponible: %s", browser_type.name, exc)
                continue

        if browser is None:
            raise RuntimeError(
                "No hay un browser local disponible para fallback. "
                "Ejecuta 'playwright install' para instalar los navegadores."
            )

        context = browser.new_context()
        page = context.new_page()
        if headers:
            page.set_extra_http_headers(headers)
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        return page.content()
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass
        try:
            if playwright is not None:
                playwright.stop()
        except Exception:
            pass


def _html_to_text(html: str, max_chars: int = 6000) -> str:
    """Convierte HTML a texto plano, eliminando scripts y estilos."""
    # Eliminar scripts y estilos
    html = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.S | re.I)
    html = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.S | re.I)
    # Eliminar etiquetas
    text = re.sub(r'<[^>]+>', ' ', html)
    # Normalizar espacios
    return ' '.join(text.split())[:max_chars]


def _clean_url(href: str) -> str:
    """Limpia y normaliza una URL extraída de DuckDuckGo."""
    href = urllib.parse.unquote(href.strip())
    if href.startswith("//"):
        href = "https:" + href
    # Desenvolver URLs de redirección de DDG (/l/?uddg=... o /url?q=...)
    parsed = urllib.parse.urlparse(href)
    qs = urllib.parse.parse_qs(parsed.query)
    if "uddg" in qs:
        href = qs["uddg"][0]
    elif "q" in qs and "duckduckgo.com" in parsed.netloc:
        href = qs["q"][0]
    return href


def _is_bot_detection_page(html: str) -> bool:
    """Detecta si el HTML es una página de detección de bots de DuckDuckGo."""
    html_lower = html.lower()
    return any(marker in html_lower for marker in _BOT_DETECTION_MARKERS)


def _parse_ddg_results(html: str, max_results: int = 5) -> list[str]:
    """Extrae resultados de DuckDuckGo HTML usando múltiples patrones de respaldo."""
    results = []
    # Usar ["'] para manejar tanto comillas dobles como simples (DDG Lite usa simples)
    patterns = [
        # Patrón principal de html.duckduckgo.com
        re.compile(
            r'<div[^>]+class="links_main links_deep result__body"[^>]*>.*?'
            r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.S,
        ),
        # Patrón alternativo: enlaces con clase result__a
        re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.S,
        ),
        # Patrón genérico: bloque result con h2 y enlace
        re.compile(
            r'<div[^>]+class="[^"]*result[^"]*"[^>]*>.*?'
            r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<div[^>]+class="[^"]*snippet[^"]*"[^>]*>(.*?)</div>',
            re.S,
        ),
        # Patrón para DDG Lite (HTML minimalista) - usa comillas simples
        re.compile(
            r'<a[^>]+href="([^"]+)"[^>]*class=["\']result-link["\'][^>]*>(.*?)</a>.*?'
            r'<td[^>]+class=["\']result-snippet["\'][^>]*>(.*?)</td>',
            re.S,
        ),
        # Patrón alternativo DDG Lite: enlace con rel=nofollow
        re.compile(
            r'<a[^>]+rel="nofollow"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<td[^>]+class=["\']result-snippet["\'][^>]*>(.*?)</td>',
            re.S,
        ),
    ]
    for pattern in patterns:
        for match in pattern.finditer(html):
            href = _clean_url(match.group(1))
            title = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            snippet = re.sub(r'<[^>]+>', '', match.group(3)).strip()
            if not title:
                continue
            results.append(f"Titulo: {title}\nURL: {href}\nResumen: {snippet or 'No disponible'}\n---")
            if len(results) >= max_results:
                return results
    return results


def _with_retries(fn, retries: int = MAX_RETRIES, base_delay: float = 1.0, backoff: float = 2.0):
    """Ejecuta fn con reintentos y backoff exponencial ante fallos transitorios."""
    last_error = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                delay = base_delay * (backoff ** attempt)
                logger.warning(
                    "Intento %d/%d falló: %s. Reintentando en %.1fs...",
                    attempt + 1, retries, exc, delay,
                )
                time.sleep(delay)
    raise last_error


@tool
def search_web_lightpanda(query: str) -> str:
    """
    Busca en la web sobre un tema especifico utilizando LightPanda y DuckDuckGo.
    Devuelve los titulos, URLs y fragmentos de resumen de los primeros 5 resultados.

    Args:
        query: La consulta o termino de busqueda.
    """
    encoded_query = urllib.parse.quote_plus(query)
    # Usar DuckDuckGo en versión HTML para evitar dependencias JS fuertes
    search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}&kl=es-es"
    lite_url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
    logger.info("Busqueda (DuckDuckGo): %s", query)
    logger.debug("DuckDuckGo search URL: %s", search_url)

    def _do_search() -> str:
        playwright = None
        context = None
        try:
            playwright, browser, _cdp_url = _connect_to_lightpanda()

            # Contexto fresco por llamada: evita interferencias entre invocaciones
            context = browser.new_context()
            context.set_default_navigation_timeout(NAV_TIMEOUT_MS)
            context.set_default_timeout(NAV_TIMEOUT_MS)
            page = context.new_page()
            page.set_extra_http_headers(DEFAULT_HEADERS)

            html_fallback = None
            page_html = None
            try:
                page.goto(search_url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector("body", timeout=max(1000, NAV_TIMEOUT_MS // 2))
                except Exception:
                    pass
                page_html = page.content()
            except Exception:
                logger.warning("Navegación con LightPanda falló, intentando navegador local")
                try:
                    html_fallback = _fetch_with_local_browser(
                        search_url, headers=DEFAULT_HEADERS, timeout_ms=NAV_TIMEOUT_MS
                    )
                except Exception:
                    logger.warning("Navegador local falló, usando fallback HTTP")
                    try:
                        html_fallback = _http_get(search_url, headers=DEFAULT_HEADERS, timeout_s=HTTP_TIMEOUT_S)
                    except Exception:
                        logger.warning("Fallback HTTP principal falló, intentando DDG Lite")
                        html_fallback = _http_get(lite_url, headers=DEFAULT_HEADERS, timeout_s=HTTP_TIMEOUT_S)

            results = []
            if html_fallback is not None:
                results = _parse_ddg_results(html_fallback)
            elif page_html is not None:
                # Verificar si LightPanda recibió una página de detección de bots
                if _is_bot_detection_page(page_html):
                    logger.warning("LightPanda recibió página de detección de bots, usando fallback HTTP")
                    try:
                        html_fallback = _http_get(search_url, headers=DEFAULT_HEADERS, timeout_s=HTTP_TIMEOUT_S)
                        results = _parse_ddg_results(html_fallback)
                    except Exception:
                        logger.warning("Fallback HTTP falló, intentando DDG Lite")
                        try:
                            lite_html = _http_get(lite_url, headers=DEFAULT_HEADERS, timeout_s=HTTP_TIMEOUT_S)
                            results = _parse_ddg_results(lite_html)
                        except Exception:
                            pass
                else:
                    results = _parse_ddg_results(page_html)
                    if not results:
                        # Extraer del DOM de la página cargada
                        try:
                            result_elements = page.locator(
                                "div.result.results_links.results_links_deep.web-result, "
                                "div.links_main.links_deep.result__body"
                            ).all()
                            if not result_elements:
                                result_elements = page.locator("div.result__body, div.result").all()

                            for elem in result_elements[:5]:
                                try:
                                    title_elem = elem.locator(
                                        "a.result__a, h2 > a, a[data-testid='result-title-link']"
                                    ).first
                                    if title_elem.count() > 0:
                                        title = title_elem.first.inner_text().strip()
                                        href = title_elem.get_attribute("href") or ""
                                        snippet_elem = elem.locator(".result__snippet, .result__extras, p").first
                                        snippet = snippet_elem.inner_text().strip() if snippet_elem.count() > 0 else ""
                                        results.append(f"Titulo: {title}\nURL: {href}\nResumen: {snippet}\n---")
                                except Exception:
                                    continue
                        except Exception:
                            pass

            if not results:
                # Último recurso: DDG Lite vía HTTP
                try:
                    lite_html = _http_get(lite_url, headers=DEFAULT_HEADERS, timeout_s=HTTP_TIMEOUT_S)
                    results = _parse_ddg_results(lite_html)
                except Exception:
                    pass

            if not results:
                return f"No se encontraron resultados para '{query}'."

            return "\n".join(results)

        finally:
            # Cerrar solo el contexto creado por esta llamada.
            # IMPORTANTE: NO llamar browser.close() en conexiones CDP remotas,
            # porque cerraría el navegador LightPanda compartido.
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass
            try:
                if playwright is not None:
                    playwright.stop()
            except Exception:
                pass

    try:
        return _with_retries(_do_search)
    except Exception as e:
        return f"Error en la busqueda para '{query}': {str(e)}"


@tool
def scrape_website_lightpanda(url: str) -> str:
    """
    Extrae el contenido de texto visible de una pagina web usando LightPanda.
    Ideal para investigar sitios web de la competencia o prospectos.

    Args:
        url: La direccion web (URL) del sitio a extraer.
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    logger.info("Scrapeando URL: %s", url)

    def _do_scrape() -> str:
        playwright = None
        context = None
        try:
            playwright, browser, _cdp_url = _connect_to_lightpanda()

            # Contexto fresco por llamada: evita interferencias entre invocaciones
            context = browser.new_context()
            context.set_default_navigation_timeout(NAV_TIMEOUT_MS)
            context.set_default_timeout(NAV_TIMEOUT_MS)
            page = context.new_page()
            page.set_extra_http_headers(DEFAULT_HEADERS)

            try:
                page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
            except Exception:
                logger.warning("Scrape navegación con LightPanda falló, probando navegador local")
                try:
                    html = _fetch_with_local_browser(
                        url, headers=DEFAULT_HEADERS, timeout_ms=NAV_TIMEOUT_MS
                    )
                    return _html_to_text(html)
                except Exception:
                    logger.warning("Scrape navegador local falló, probando HTTP simple")
                    try:
                        html = _http_get(url, headers=DEFAULT_HEADERS, timeout_s=HTTP_TIMEOUT_S)
                        return _html_to_text(html)
                    except Exception:
                        raise

            text = page.locator("body").inner_text()
            return " ".join(text.split())[:6000]

        finally:
            # Cerrar solo el contexto creado por esta llamada.
            # IMPORTANTE: NO llamar browser.close() en conexiones CDP remotas,
            # porque cerraría el navegador LightPanda compartido.
            try:
                if context is not None:
                    context.close()
            except Exception:
                pass
            try:
                if playwright is not None:
                    playwright.stop()
            except Exception:
                pass

    try:
        return _with_retries(_do_scrape)
    except Exception as e:
        logger.exception("Error scraping %s", url)
        return f"Error al extraer contenido de {url}: {str(e)}"
