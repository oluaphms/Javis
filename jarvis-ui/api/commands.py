"""
commands.py — Motor de interpretação e execução de comandos do sistema.

Arquitetura:
    - CommandResult: resultado tipado de cada execução
    - CommandRegistry: registro desacoplado de handlers
    - Handlers organizados por categoria (apps, sistema, web, info)
    - Suporte a argumentos dinâmicos extraídos do texto
    - Ações perigosas com flag de confirmação
    - Fácil adição de novos comandos via @registry.register(...)

Uso:
    from commands import execute_command, list_commands
    result = execute_command("abrir chrome")
    print(result.message)
"""

import subprocess
import os
import sys
import platform
import logging
import webbrowser
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ─── Tipos ────────────────────────────────────────────────────────────────────


@dataclass
class CommandResult:
    """
    Resultado padronizado de uma execução de comando.

    Attributes:
        success:        True se o comando foi executado sem erros.
        message:        Mensagem legível para o usuário.
        command_name:   Nome do handler que foi executado.
        requires_confirm: True se o comando precisa de confirmação humana.
        data:           Dados extras opcionais (dicionário livre).
    """
    success: bool
    message: str
    command_name: str = ""
    requires_confirm: bool = False
    data: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


@dataclass
class CommandHandler:
    """Metadados de um handler registrado."""
    name: str
    description: str
    keywords: list[str]
    category: str
    dangerous: bool
    fn: Callable


# ─── Registro Central ─────────────────────────────────────────────────────────


class CommandRegistry:
    """
    Registro desacoplado de handlers de comandos.

    Permite adicionar comandos sem modificar o motor de execução.
    Cada handler é uma função que recebe o texto original e retorna CommandResult.
    """

    def __init__(self):
        self._handlers: list[CommandHandler] = []

    def register(
        self,
        keywords: list[str],
        description: str = "",
        category: str = "geral",
        dangerous: bool = False,
    ):
        """
        Decorator para registrar um novo handler.

        Args:
            keywords:    Palavras/frases que ativam o comando.
            description: Descrição legível para humanos.
            category:    Categoria para agrupamento (apps, sistema, web, info).
            dangerous:   Se True, retorna requires_confirm=True sem executar.

        Exemplo:
            @registry.register(["abrir spotify"], category="apps")
            def cmd_spotify(text: str) -> CommandResult:
                subprocess.Popen("spotify.exe")
                return CommandResult(True, "Spotify aberto!")
        """
        def decorator(fn: Callable) -> Callable:
            self._handlers.append(CommandHandler(
                name=fn.__name__,
                description=description or (fn.__doc__ or "").strip().split("\n")[0],
                keywords=[kw.lower() for kw in keywords],
                category=category,
                dangerous=dangerous,
                fn=fn,
            ))
            logger.debug(f"Comando registrado: {fn.__name__} | keywords={keywords}")
            return fn
        return decorator

    def match(self, text: str) -> Optional[CommandHandler]:
        """Retorna o primeiro handler que corresponde ao texto."""
        text_lower = text.lower()
        for handler in self._handlers:
            if any(kw in text_lower for kw in handler.keywords):
                return handler
        return None

    def execute(self, text: str) -> Optional[CommandResult]:
        """
        Encontra e executa o handler correspondente ao texto.
        Retorna None se nenhum comando for reconhecido.
        """
        handler = self.match(text)
        if handler is None:
            return None

        # Ações perigosas não executam: pedem confirmação
        if handler.dangerous:
            logger.warning(f"Comando perigoso bloqueado: '{handler.name}'")
            return CommandResult(
                success=False,
                message=f"⚠️ '{handler.description}' é uma ação perigosa. Confirme manualmente.",
                command_name=handler.name,
                requires_confirm=True,
            )

        try:
            logger.info(f"Executando: {handler.name} para '{text}'")
            result = handler.fn(text)
            result.command_name = handler.name
            return result
        except FileNotFoundError as e:
            msg = f"Programa não encontrado: {e.filename}"
            logger.error(msg)
            return CommandResult(False, msg, command_name=handler.name)
        except PermissionError:
            msg = "Sem permissão para executar este comando."
            logger.error(msg)
            return CommandResult(False, msg, command_name=handler.name)
        except Exception as e:
            msg = f"Erro inesperado: {str(e)}"
            logger.exception(msg)
            return CommandResult(False, msg, command_name=handler.name)

    def list_all(self) -> list[dict]:
        """Retorna todos os comandos registrados como lista de dicionários."""
        return [
            {
                "name": h.name,
                "description": h.description,
                "keywords": h.keywords,
                "category": h.category,
                "dangerous": h.dangerous,
            }
            for h in self._handlers
        ]

    def list_by_category(self) -> dict[str, list[dict]]:
        """Retorna os comandos agrupados por categoria."""
        grouped: dict[str, list] = {}
        for h in self._handlers:
            grouped.setdefault(h.category, []).append({
                "name": h.name,
                "description": h.description,
                "keywords": h.keywords,
            })
        return grouped


# Instância global compartilhada
registry = CommandRegistry()


# ─── Funções Auxiliares ───────────────────────────────────────────────────────

def _open_app(executable: str, display_name: str) -> CommandResult:
    """Tenta abrir um executável. Suporta Windows, macOS e Linux."""
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(executable)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", executable])
        else:
            subprocess.Popen([executable])
        return CommandResult(True, f"{display_name} aberto com sucesso.")
    except FileNotFoundError:
        # Tenta via 'where' (Windows) ou 'which' (Unix)
        cmd = "where" if system == "Windows" else "which"
        found = subprocess.run([cmd, executable], capture_output=True, text=True).returncode == 0
        if not found:
            return CommandResult(False, f"{display_name} não encontrado no sistema.")
        raise


def _extract_arg(text: str, keywords: list[str]) -> str:
    """Extrai o argumento após uma keyword no texto."""
    text_lower = text.lower()
    for kw in sorted(keywords, key=len, reverse=True):  # mais longa primeiro
        if kw in text_lower:
            after = text_lower.split(kw, 1)[-1].strip()
            if after:
                return after
    return ""


# ─── Categoria: Navegadores ───────────────────────────────────────────────────

@registry.register(
    keywords=["abrir chrome", "open chrome", "chrome"],
    description="Abre o Google Chrome",
    category="apps",
)
def cmd_chrome(text: str) -> CommandResult:
    """Abre o Google Chrome."""
    for exe in ["chrome", "google-chrome", "chromium"]:
        result = _open_app(exe, "Chrome")
        if result.success:
            return result
    return CommandResult(False, "Google Chrome não encontrado. Verifique a instalação.")


@registry.register(
    keywords=["abrir firefox", "firefox"],
    description="Abre o Mozilla Firefox",
    category="apps",
)
def cmd_firefox(text: str) -> CommandResult:
    """Abre o Mozilla Firefox."""
    return _open_app("firefox", "Firefox")


@registry.register(
    keywords=["abrir navegador", "open browser", "browser"],
    description="Abre o navegador padrão do sistema",
    category="apps",
)
def cmd_browser(text: str) -> CommandResult:
    """Abre o navegador padrão."""
    webbrowser.open("https://www.google.com")
    return CommandResult(True, "Navegador padrão aberto.")


# ─── Categoria: IDEs e Editores ───────────────────────────────────────────────

@registry.register(
    keywords=["abrir vscode", "abrir visual studio code", "vscode", "code"],
    description="Abre o Visual Studio Code",
    category="apps",
)
def cmd_vscode(text: str) -> CommandResult:
    """Abre o Visual Studio Code."""
    # 'code' é o CLI do VSCode adicionado ao PATH pelo instalador
    if shutil.which("code"):
        subprocess.Popen(["code"])
        return CommandResult(True, "Visual Studio Code aberto.")
    # Tenta o executável direto no Windows
    vscode_path = os.path.expandvars(
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
    )
    if os.path.exists(vscode_path):
        subprocess.Popen([vscode_path])
        return CommandResult(True, "Visual Studio Code aberto.")
    return CommandResult(False, "VS Code não encontrado. Instale em https://code.visualstudio.com")


@registry.register(
    keywords=["abrir bloco de notas", "notepad", "bloco de notas"],
    description="Abre o Bloco de Notas",
    category="apps",
)
def cmd_notepad(text: str) -> CommandResult:
    """Abre o Bloco de Notas (Windows)."""
    if platform.system() != "Windows":
        return CommandResult(False, "Bloco de notas disponível apenas no Windows.")
    subprocess.Popen("notepad.exe")
    return CommandResult(True, "Bloco de notas aberto.")


@registry.register(
    keywords=["abrir calculadora", "calculadora", "calculator"],
    description="Abre a Calculadora",
    category="apps",
)
def cmd_calculator(text: str) -> CommandResult:
    """Abre a Calculadora."""
    system = platform.system()
    if system == "Windows":
        subprocess.Popen("calc.exe")
    elif system == "Darwin":
        subprocess.Popen(["open", "-a", "Calculator"])
    else:
        for calc in ["gnome-calculator", "kcalc", "xcalc"]:
            if shutil.which(calc):
                subprocess.Popen([calc])
                break
    return CommandResult(True, "Calculadora aberta.")


@registry.register(
    keywords=["abrir terminal", "abrir cmd", "abrir powershell", "terminal", "prompt"],
    description="Abre o terminal do sistema",
    category="apps",
)
def cmd_terminal(text: str) -> CommandResult:
    """Abre o terminal padrão."""
    system = platform.system()
    if system == "Windows":
        # Tenta Windows Terminal, depois PowerShell, depois cmd
        if shutil.which("wt"):
            subprocess.Popen("wt")
        else:
            subprocess.Popen("powershell.exe")
    elif system == "Darwin":
        subprocess.Popen(["open", "-a", "Terminal"])
    else:
        for term in ["gnome-terminal", "konsole", "xterm"]:
            if shutil.which(term):
                subprocess.Popen([term])
                break
    return CommandResult(True, "Terminal aberto.")


@registry.register(
    keywords=["abrir explorador", "abrir explorer", "explorador de arquivos", "file explorer"],
    description="Abre o explorador de arquivos",
    category="apps",
)
def cmd_explorer(text: str) -> CommandResult:
    """Abre o explorador de arquivos."""
    system = platform.system()
    if system == "Windows":
        subprocess.Popen("explorer.exe")
    elif system == "Darwin":
        subprocess.Popen(["open", os.path.expanduser("~")])
    else:
        for fm in ["nautilus", "dolphin", "thunar"]:
            if shutil.which(fm):
                subprocess.Popen([fm])
                break
    return CommandResult(True, "Explorador de arquivos aberto.")


# ─── Categoria: Web ───────────────────────────────────────────────────────────

@registry.register(
    keywords=["pesquisar", "buscar", "google", "search"],
    description="Pesquisa algo no Google",
    category="web",
)
def cmd_search(text: str) -> CommandResult:
    """Pesquisa no Google."""
    query = _extract_arg(text, [
        "pesquisar por", "pesquisar", "buscar por", "buscar",
        "search for", "search", "google"
    ])
    if query:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return CommandResult(True, f"Pesquisando por '{query}'.", data={"query": query, "url": url})
    webbrowser.open("https://www.google.com")
    return CommandResult(True, "Google aberto.")


@registry.register(
    keywords=["abrir youtube", "youtube"],
    description="Abre o YouTube",
    category="web",
)
def cmd_youtube(text: str) -> CommandResult:
    """Abre o YouTube."""
    query = _extract_arg(text, ["pesquisar no youtube", "youtube"])
    if query:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        return CommandResult(True, f"Pesquisando '{query}' no YouTube.")
    webbrowser.open("https://www.youtube.com")
    return CommandResult(True, "YouTube aberto.")


@registry.register(
    keywords=["abrir github", "github"],
    description="Abre o GitHub",
    category="web",
)
def cmd_github(text: str) -> CommandResult:
    """Abre o GitHub."""
    webbrowser.open("https://github.com")
    return CommandResult(True, "GitHub aberto.")


# ─── Categoria: Informações do Sistema ───────────────────────────────────────

@registry.register(
    keywords=["que horas", "hora atual", "que hora", "horas", "what time"],
    description="Informa a hora atual",
    category="info",
)
def cmd_time(text: str) -> CommandResult:
    """Retorna a hora atual."""
    now = datetime.now()
    hora = now.strftime("%H:%M:%S")
    return CommandResult(True, f"São {hora}.", data={"hora": hora})


@registry.register(
    keywords=["que dia", "data hoje", "data atual", "que data", "what date"],
    description="Informa a data atual",
    category="info",
)
def cmd_date(text: str) -> CommandResult:
    """Retorna a data de hoje."""
    today = datetime.now()
    data = today.strftime("%d/%m/%Y")
    dia_semana = today.strftime("%A")
    # Tradução simples dos dias
    dias_pt = {
        "Monday": "segunda-feira", "Tuesday": "terça-feira",
        "Wednesday": "quarta-feira", "Thursday": "quinta-feira",
        "Friday": "sexta-feira", "Saturday": "sábado", "Sunday": "domingo",
    }
    return CommandResult(
        True,
        f"Hoje é {dias_pt.get(dia_semana, dia_semana)}, {data}.",
        data={"data": data, "dia_semana": dia_semana},
    )


@registry.register(
    keywords=["sistema operacional", "qual sistema", "versão do sistema", "os info"],
    description="Informa o sistema operacional",
    category="info",
)
def cmd_os_info(text: str) -> CommandResult:
    """Retorna informações do sistema operacional."""
    info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    return CommandResult(True, f"Sistema: {info}", data={"os": info})


@registry.register(
    keywords=["versão do python", "python version", "qual python"],
    description="Informa a versão do Python",
    category="info",
)
def cmd_python_version(text: str) -> CommandResult:
    """Retorna a versão do Python em execução."""
    ver = sys.version.split()[0]
    return CommandResult(True, f"Python {ver} em execução.", data={"version": ver})


# ─── Categoria: Sistema (Perigosos) ───────────────────────────────────────────

@registry.register(
    keywords=["desligar", "desligar computador", "shutdown"],
    description="Desliga o computador",
    category="sistema",
    dangerous=True,
)
def cmd_shutdown(text: str) -> CommandResult:
    """Desliga o computador (requer confirmação)."""
    # Só executa se esta função for invocada diretamente com confirm=True
    system = platform.system()
    if system == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
        return CommandResult(True, "Computador será desligado em 30 segundos. Use 'shutdown /a' para cancelar.")
    else:
        subprocess.run(["shutdown", "-h", "+1"], check=True)
        return CommandResult(True, "Computador será desligado em 1 minuto.")


@registry.register(
    keywords=["reiniciar", "reiniciar computador", "restart"],
    description="Reinicia o computador",
    category="sistema",
    dangerous=True,
)
def cmd_restart(text: str) -> CommandResult:
    """Reinicia o computador (requer confirmação)."""
    system = platform.system()
    if system == "Windows":
        subprocess.run(["shutdown", "/r", "/t", "30"], check=True)
        return CommandResult(True, "Computador será reiniciado em 30 segundos.")
    else:
        subprocess.run(["reboot"], check=True)
        return CommandResult(True, "Reiniciando o computador...")


@registry.register(
    keywords=["bloquear tela", "lock screen", "bloquear computador"],
    description="Bloqueia a tela do computador",
    category="sistema",
)
def cmd_lock_screen(text: str) -> CommandResult:
    """Bloqueia a tela."""
    system = platform.system()
    if system == "Windows":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return CommandResult(True, "Tela bloqueada.")
    elif system == "Darwin":
        subprocess.run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])
        return CommandResult(True, "Tela bloqueada.")
    else:
        subprocess.run(["loginctl", "lock-session"])
        return CommandResult(True, "Tela bloqueada.")


@registry.register(
    keywords=["volume alto", "aumentar volume", "volume mais"],
    description="Aumenta o volume do sistema",
    category="sistema",
)
def cmd_volume_up(text: str) -> CommandResult:
    """Aumenta o volume do sistema (Windows)."""
    if platform.system() != "Windows":
        return CommandResult(False, "Controle de volume automático disponível apenas no Windows.")
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = volume.GetMasterVolumeLevelScalar()
        new_vol = min(1.0, current + 0.1)
        volume.SetMasterVolumeLevelScalar(new_vol, None)
        return CommandResult(True, f"Volume aumentado para {int(new_vol * 100)}%.", data={"volume": int(new_vol * 100)})
    except ImportError:
        return CommandResult(False, "Instale 'pycaw' para controle de volume: pip install pycaw")


@registry.register(
    keywords=["volume baixo", "diminuir volume", "volume menos"],
    description="Diminui o volume do sistema",
    category="sistema",
)
def cmd_volume_down(text: str) -> CommandResult:
    """Diminui o volume do sistema (Windows)."""
    if platform.system() != "Windows":
        return CommandResult(False, "Controle de volume automático disponível apenas no Windows.")
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        current = volume.GetMasterVolumeLevelScalar()
        new_vol = max(0.0, current - 0.1)
        volume.SetMasterVolumeLevelScalar(new_vol, None)
        return CommandResult(True, f"Volume diminuído para {int(new_vol * 100)}%.", data={"volume": int(new_vol * 100)})
    except ImportError:
        return CommandResult(False, "Instale 'pycaw' para controle de volume: pip install pycaw")


# ─── Interface Pública ────────────────────────────────────────────────────────

def execute_command(text: str) -> Optional[CommandResult]:
    """
    Ponto de entrada principal.
    Interpreta o texto e executa o comando correspondente.

    Args:
        text: Texto digitado ou reconhecido por voz.

    Returns:
        CommandResult com o resultado, ou None se nenhum comando for reconhecido.

    Exemplo:
        result = execute_command("abrir chrome")
        if result:
            print(result.message)
    """
    if not text or not text.strip():
        return None
    return registry.execute(text.strip())


def list_commands() -> list[dict]:
    """Retorna todos os comandos registrados."""
    return registry.list_all()


def list_commands_by_category() -> dict[str, list[dict]]:
    """Retorna comandos agrupados por categoria."""
    return registry.list_by_category()


def execute_dangerous(text: str) -> Optional[CommandResult]:
    """
    Executa um comando marcado como perigoso, ignorando a proteção.
    ATENÇÃO: Use apenas após confirmação explícita do usuário.
    """
    handler = registry.match(text)
    if handler is None:
        return None
    if not handler.dangerous:
        return execute_command(text)
    try:
        result = handler.fn(text)
        result.command_name = handler.name
        return result
    except Exception as e:
        return CommandResult(False, f"Erro: {str(e)}", command_name=handler.name)
