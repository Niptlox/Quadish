"""Проверка обновлений: узнать, вышел ли релиз новее текущего, и скачать его.

Релизы игры публикуются автоматически по тегу (`.github/workflows/release.yml`),
а игрок об этом не узнаёт: скачал сборку один раз — и остался на ней. Здесь
самая простая честная схема — спросить у GitHub последний релиз, сравнить
версии, и если новее, скачать архив для своей платформы в папку рядом с игрой.

Сеть здесь трогается **только в фоновом потоке** (`UpdateChecker`): игровой
цикл не должен вставать на несколько секунд из-за медленного ответа сервера,
а без интернета игра обязана работать ровно как раньше.

Распаковка и подмена файлов **намеренно не делаются**: заменять запущенный
исполняемый файл из него же — источник битых установок, у каждой платформы
это делается по-своему. Игра скачивает архив и показывает, куда — дальше
решает игрок.
"""
import json
import os
import platform
import re
import threading
import urllib.error
import urllib.request

REPO = "Niptlox/Quadish"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 8
DOWNLOAD_DIR = "downloads"
USER_AGENT = "Quadish-updater"

_VERSION_RE = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_version(text):
    """"v0.2.16-alpha" -> (0, 2, 16). Ведущая "v" и суффикс не мешают.

    Возвращает None, если чисел в строке нет — тогда сравнивать нечего и
    вызывающий код просто не считает версию новее.
    """
    if not text:
        return None
    m = _VERSION_RE.search(str(text))
    if not m:
        return None
    return tuple(int(g) if g else 0 for g in m.groups())


def is_newer(remote, local):
    """Строго новее ли remote, чем local. Неразбираемая версия — не новее."""
    r, l = parse_version(remote), parse_version(local)
    if r is None or l is None:
        return False
    return r > l


def platform_asset_suffix():
    """Как называется архив для этой ОС (см. release.yml, шаги Package)."""
    system = platform.system()
    if system == "Windows":
        return "windows-x64.zip"
    if system == "Linux":
        return "linux-x64.tar.gz"
    return None          # macOS-сборок пока нет — качать нечего


def _request(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def fetch_latest():
    """Последний релиз: {"tag", "url", "assets": {имя: ссылка}} или None.

    None означает «не удалось спросить» (нет сети, лимит GitHub, таймаут) —
    это не ошибка игры и не должно ничего ломать.
    """
    try:
        with _request(API_LATEST) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None
    tag = data.get("tag_name")
    if not tag:
        return None
    assets = {a.get("name"): a.get("browser_download_url")
              for a in data.get("assets", []) if a.get("name")}
    return {"tag": tag, "url": data.get("html_url") or RELEASES_PAGE, "assets": assets}


def asset_for_platform(assets):
    """(имя, ссылка) архива для текущей ОС или None."""
    suffix = platform_asset_suffix()
    if not suffix:
        return None
    for name, url in assets.items():
        if name.endswith(suffix):
            return name, url
    return None


def download(url, name, directory=DOWNLOAD_DIR, on_progress=None):
    """Скачать файл в directory/name, вернуть путь.

    Пишем во временный файл и переименовываем в конце: оборванная закачка
    не должна оставить файл, который выглядит как готовый архив.
    """
    os.makedirs(directory, exist_ok=True)
    dest = os.path.join(directory, name)
    tmp = dest + ".part"
    with _request(url, accept="application/octet-stream") as resp, open(tmp, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if on_progress and total:
                on_progress(done / total)
    os.replace(tmp, dest)
    return dest


class UpdateChecker:
    """Проверка и загрузка в фоне; UI только читает поля.

    Состояния: idle → checking → (uptodate | available | error);
    из available: downloading → (downloaded | error).
    """
    IDLE, CHECKING, UPTODATE, AVAILABLE, DOWNLOADING, DOWNLOADED, ERROR = (
        "idle", "checking", "uptodate", "available", "downloading", "downloaded", "error")

    def __init__(self, current_version):
        self.current_version = current_version
        self.state = self.IDLE
        self.latest_tag = None
        self.release_url = RELEASES_PAGE
        self.asset = None          # (имя, ссылка) для этой ОС
        self.progress = 0.0
        self.path = None           # куда скачали
        self.message = ""
        self._thread = None

    def busy(self):
        return self.state in (self.CHECKING, self.DOWNLOADING)

    def check_async(self):
        if self.busy():
            return
        self.state = self.CHECKING
        self.message = "Проверяю обновления…"
        self._start(self._check)

    def download_async(self):
        if self.busy() or self.state != self.AVAILABLE or not self.asset:
            return
        self.state = self.DOWNLOADING
        self.progress = 0.0
        self.message = "Скачиваю…"
        self._start(self._download)

    def _start(self, target):
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def _check(self):
        info = fetch_latest()
        if info is None:
            self.state = self.ERROR
            self.message = "Не удалось проверить обновления"
            return
        self.latest_tag = info["tag"]
        self.release_url = info["url"]
        if not is_newer(info["tag"], self.current_version):
            self.state = self.UPTODATE
            self.message = "Установлена последняя версия"
            return
        self.asset = asset_for_platform(info["assets"])
        self.state = self.AVAILABLE
        if self.asset:
            self.message = f"Доступна {info['tag']} — можно скачать"
        else:
            # Сборки для этой ОС нет — честно говорим об этом, а не
            # предлагаем кнопку, которая ничего не скачает.
            self.message = f"Доступна {info['tag']} (сборки для вашей ОС нет)"

    def _download(self):
        name, url = self.asset
        try:
            self.path = download(url, name, on_progress=self._on_progress)
        except (urllib.error.URLError, OSError, TimeoutError):
            self.state = self.ERROR
            self.message = "Не удалось скачать обновление"
            return
        self.state = self.DOWNLOADED
        self.progress = 1.0
        self.message = f"Скачано: {self.path}"

    def _on_progress(self, value):
        self.progress = value
