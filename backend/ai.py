"""
ai.py — Motor de Inteligência Artificial do Jarvis.

Arquitetura em 3 camadas:
    1. Intenção    → AIIntentDetector: classifica o que o usuário quer
    2. Provider    → AIProvider (interface) + implementações concretas
    3. Orquestrador → AIEngine: escolhe o provider, gerencia histórico e fallback

Providers suportados (em ordem de prioridade):
    ┌─────────────────┬──────────────┬──────────────────────────────────┐
    │ Provider        │ Config       │ Observação                       │
    ├─────────────────┼──────────────┼──────────────────────────────────┤
    │ OpenAI          │ OPENAI_API_KEY │ GPT-3.5/4, pago               │
    │ Groq            │ GROQ_API_KEY  │ LLaMA3, gratuito, ultra-rápido │
    │ Google Gemini   │ GEMINI_API_KEY│ Gemini Flash, gratuito         │
    │ Fallback Local  │ —             │ Sempre disponível, sem internet │
    └─────────────────┴──────────────┴──────────────────────────────────┘

Uso:
    from ai import process_query, get_ai_info, clear_history
    reply = process_query("quais são minhas tarefas?")
"""

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import config

logger = logging.getLogger(__name__)


# ─── Tipos ────────────────────────────────────────────────────────────────────

@dataclass
class AIResponse:
    """Resposta padronizada do motor de IA."""
    text: str
    provider: str           # nome do provider usado
    intent: str             # intenção detectada
    from_cache: bool = False
    error: Optional[str] = None

    def __str__(self) -> str:
        return self.text


@dataclass
class ConversationTurn:
    """Um turno de conversa (par pergunta/resposta)."""
    role: str    # "user" | "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


# ─── Detector de Intenção ─────────────────────────────────────────────────────

class AIIntentDetector:
    """
    Classifica a intenção do usuário para fornecer contexto ao prompt.
    Permite que o sistema prompt seja adaptado dinamicamente.
    """

    _INTENTS = [
        ("saudacao",      r"^(oi|olá|boa\s*\w+|hello|hi|e\s*aí|salve)\b"),
        ("despedida",     r"\b(tchau|até\s*logo|bye|adeus|sair|encerrar)\b"),
        ("agradecimento", r"\b(obrigad|valeu|thanks|grato|grata)\b"),
        ("ajuda",         r"\b(ajuda|help|o\s*que\s*(você\s*)?(pode|sabe|faz)|comandos\s*disponíveis)\b"),
        ("tarefa_criar",  r"\b(criar?|adicionar?|nova?|incluir?)\s+tarefa\b"),
        ("tarefa_listar", r"\b(listar?|mostrar?|ver?|quais?)\s+(minhas?\s+)?tarefa\b"),
        ("tarefa_conc",   r"\b(concluir?|finalizar?|terminar?|completar?)\s+tarefa\b"),
        ("sistema_info",  r"\b(status|estado\s+do?\s+sistema|versão|version)\b"),
        ("pergunta_ia",   r"\b(o\s*que\s*é|como\s*funciona|explique?|defina?|me\s*diga)\b"),
        ("matematica",    r"\b(\d+\s*[\+\-\*\/\%\^]\s*\d+|calcule?|quanto\s*é)\b"),
        ("clima",         r"\b(clima|tempo\s+em|temperatura|vai\s+chover)\b"),
        ("geral",         r".*"),  # sempre casa por último
    ]

    _compiled = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in _INTENTS]

    @classmethod
    def detect(cls, text: str) -> str:
        """Retorna o nome da intenção mais provável."""
        for name, pattern in cls._compiled:
            if pattern.search(text):
                return name
        return "geral"

    @classmethod
    def get_context_hint(cls, intent: str) -> str:
        """Retorna uma dica de contexto para enriquecer o prompt do sistema."""
        hints = {
            "tarefa_criar":  "O usuário quer criar uma tarefa. Confirme os detalhes se necessário.",
            "tarefa_listar": "O usuário quer ver suas tarefas. Direcione-o ao painel de tarefas.",
            "tarefa_conc":   "O usuário quer concluir uma tarefa. Peça o número ou nome da tarefa.",
            "matematica":    "Resolva o cálculo diretamente com o resultado numérico.",
            "pergunta_ia":   "Responda de forma educativa e concisa.",
            "clima":         "Não tenho acesso à internet. Informe isso gentilmente.",
            "ajuda":         "Liste as principais capacidades do Jarvis de forma organizada.",
        }
        return hints.get(intent, "")


# ─── Interface de Provider ────────────────────────────────────────────────────

class AIProvider(ABC):
    """Interface base para todos os providers de IA."""

    SYSTEM_PROMPT = f"""Você é {config.JARVIS_NAME}, um assistente de produtividade inteligente e direto.
Regras obrigatórias:
- Responda SEMPRE em português do Brasil
- Seja conciso: máximo 3 linhas, salvo pedido detalhado
- Nunca revele que é um chatbot genérico; você é o {config.JARVIS_NAME}
- Se não souber algo, diga claramente em vez de inventar
- Confirmações de ações devem ser claras e objetivas"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador do provider."""

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provider está configurado e disponível."""

    @abstractmethod
    def complete(self, messages: list[dict], intent: str) -> str:
        """Envia os mensagens e retorna a resposta em texto."""

    def build_messages(
        self,
        history: list[ConversationTurn],
        current_text: str,
        intent: str,
    ) -> list[dict]:
        """
        Monta a lista de mensagens no formato OpenAI-compatible.
        Adiciona dica de contexto baseada na intenção detectada.
        """
        hint = AIIntentDetector.get_context_hint(intent)
        system = self.SYSTEM_PROMPT
        if hint:
            system += f"\n\nContexto desta mensagem: {hint}"

        msgs = [{"role": "system", "content": system}]
        # Histórico recente (máx. 10 turnos = 20 mensagens)
        for turn in history[-20:]:
            msgs.append({"role": turn.role, "content": turn.content})
        msgs.append({"role": "user", "content": current_text})
        return msgs


# ─── Provider: OpenAI ─────────────────────────────────────────────────────────

class OpenAIProvider(AIProvider):
    """Provider OpenAI GPT — gpt-3.5-turbo, gpt-4, etc."""

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    def complete(self, messages: list[dict], intent: str) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                max_tokens=config.AI_MAX_TOKENS,
                temperature=config.AI_TEMPERATURE,
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            raise RuntimeError("Instale o pacote openai: pip install openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI erro: {e}") from e


# ─── Provider: Groq ───────────────────────────────────────────────────────────

class GroqProvider(AIProvider):
    """
    Provider Groq — inferência ultra-rápida com LLaMA3.
    API gratuita: https://console.groq.com
    Compatível com a biblioteca openai (mesmo formato de API).
    """

    @property
    def name(self) -> str:
        return "groq"

    def is_available(self) -> bool:
        return bool(config.GROQ_API_KEY)

    def complete(self, messages: list[dict], intent: str) -> str:
        try:
            import openai
            client = openai.OpenAI(
                api_key=config.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
            )
            response = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                max_tokens=config.AI_MAX_TOKENS,
                temperature=config.AI_TEMPERATURE,
            )
            return response.choices[0].message.content.strip()
        except ImportError:
            raise RuntimeError("Instale o pacote openai: pip install openai")
        except Exception as e:
            raise RuntimeError(f"Groq erro: {e}") from e


# ─── Provider: Google Gemini ──────────────────────────────────────────────────

class GeminiProvider(AIProvider):
    """
    Provider Google Gemini — gemini-1.5-flash (gratuito).
    API gratuita: https://aistudio.google.com/apikey
    """

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(config.GEMINI_API_KEY)

    def complete(self, messages: list[dict], intent: str) -> str:
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=config.GEMINI_MODEL,
                system_instruction=self.SYSTEM_PROMPT,
            )
            # Converte formato OpenAI → Gemini
            conversation = model.start_chat(history=[
                {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]}
                for m in messages
                if m["role"] in ("user", "assistant")
            ][:-1])  # último é a mensagem atual
            last_user = next(
                m["content"] for m in reversed(messages) if m["role"] == "user"
            )
            response = conversation.send_message(last_user)
            return response.text.strip()
        except ImportError:
            raise RuntimeError("Instale: pip install google-generativeai")
        except Exception as e:
            raise RuntimeError(f"Gemini erro: {e}") from e


# ─── Provider: Fallback Local ─────────────────────────────────────────────────

class LocalFallbackProvider(AIProvider):
    """
    Provider local baseado em intenções e padrões regex.
    Sempre disponível — não requer internet nem API key.
    Respostas amigáveis e contextuais baseadas na intenção detectada.
    """

    @property
    def name(self) -> str:
        return "local_fallback"

    def is_available(self) -> bool:
        return True  # sempre disponível

    # Mapa de intenção → resposta(s) possíveis
    _INTENT_RESPONSES: dict[str, list[str]] = {
        "saudacao": [
            "Olá! Sou o Jarvis, seu assistente de produtividade. Como posso ajudar?",
            "Oi! Pronto para produzir. O que você precisa hoje?",
        ],
        "despedida": [
            "Até logo! Estarei aqui quando precisar.",
            "Tchau! Qualquer coisa é só chamar.",
        ],
        "agradecimento": [
            "De nada! Fico feliz em ajudar.",
            "Disponha! Estou aqui para isso.",
        ],
        "ajuda": [
            (
                "Posso ajudar com:\n"
                "• Criar/listar/concluir tarefas\n"
                "• Abrir programas (Chrome, VSCode, Notepad...)\n"
                "• Pesquisar no Google e YouTube\n"
                "• Informar hora, data e status do sistema\n"
                "• Responder perguntas gerais\n"
                "Configure OPENAI_API_KEY ou GROQ_API_KEY para respostas mais inteligentes!"
            )
        ],
        "tarefa_criar": [
            "Para criar uma tarefa, use o painel de tarefas à direita ou diga: 'criar tarefa [nome da tarefa]'.",
        ],
        "tarefa_listar": [
            "Suas tarefas estão no painel à direita. Você pode filtrar por status (pendente, em andamento, concluída).",
        ],
        "tarefa_conc": [
            "Para concluir uma tarefa, clique em '✓ Concluir' no painel de tarefas ou diga o número da tarefa.",
        ],
        "sistema_info": [
            f"Sistema Jarvis v{config.JARVIS_VERSION} operacional. IA em modo local (configure uma API key para IA online).",
        ],
        "matematica": [],  # calculado dinamicamente
        "geral": [],       # resposta genérica dinâmica
    }

    # Padrões regex para respostas dinâmicas
    _DYNAMIC_PATTERNS = [
        # Cumprimentos com horário
        (r"\b(bom\s*dia)\b",     "Bom dia! Espero que você tenha um dia produtivo. Como posso ajudar?"),
        (r"\b(boa\s*tarde)\b",   "Boa tarde! Em que posso ajudar agora?"),
        (r"\b(boa\s*noite)\b",   "Boa noite! Ainda tem algo para fazer hoje?"),
        # Cálculos simples
        (r"(\d+)\s*\+\s*(\d+)",  None),   # calculado em runtime
        (r"(\d+)\s*\-\s*(\d+)",  None),
        (r"(\d+)\s*\*\s*(\d+)",  None),
        (r"(\d+)\s*\/\s*(\d+)",  None),
        # Nome do assistente
        (r"\b(seu\s*nome|como\s*(te|você)\s*chama)",
         f"Meu nome é {config.JARVIS_NAME}. Sou seu assistente de produtividade pessoal."),
        # Versão
        (r"\b(sua\s*versão|version)",
         f"Estou na versão {config.JARVIS_VERSION}. Compilado para máxima produtividade!"),
    ]

    def complete(self, messages: list[dict], intent: str) -> str:
        # Pega o texto do usuário (última mensagem)
        user_text = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            ""
        )
        return self._generate_response(user_text, intent)

    def _generate_response(self, text: str, intent: str) -> str:
        text_lower = text.lower()

        # 1. Tenta padrões dinâmicos (ex: cálculos)
        dynamic = self._try_dynamic(text_lower)
        if dynamic:
            return dynamic

        # 2. Tenta respostas por intenção
        candidates = self._INTENT_RESPONSES.get(intent, [])
        if candidates:
            import random
            return random.choice(candidates)

        # 3. Resposta genérica informativa
        return (
            "Entendi sua mensagem, mas ainda estou em modo local sem IA online. "
            f"Configure OPENAI_API_KEY, GROQ_API_KEY ou GEMINI_API_KEY para respostas mais inteligentes. "
            "Por ora, posso ajudar com tarefas, abrir programas e informações do sistema."
        )

    def _try_dynamic(self, text: str) -> Optional[str]:
        """Tenta responder com padrões dinâmicos (cálculos, saudações com horário, etc.)."""
        # Cálculos simples
        calc_match = re.search(r"(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)", text)
        if calc_match:
            try:
                a   = float(calc_match.group(1))
                op  = calc_match.group(2)
                b   = float(calc_match.group(3))
                ops = {"+": a + b, "-": a - b, "*": a * b, "/": a / b if b != 0 else None}
                result = ops.get(op)
                if result is None:
                    return "Erro: divisão por zero."
                result_str = int(result) if result == int(result) else round(result, 4)
                return f"O resultado de {a:g} {op} {b:g} = **{result_str}**"
            except Exception:
                pass

        # Padrões de texto estático
        for pattern, response in self._DYNAMIC_PATTERNS:
            if response and re.search(pattern, text, re.IGNORECASE):
                return response

        return None


# ─── Orquestrador de IA ───────────────────────────────────────────────────────

class AIEngine:
    """
    Orquestrador central do sistema de IA.

    Responsabilidades:
        - Detectar intenção do usuário
        - Selecionar o melhor provider disponível
        - Gerenciar histórico de conversa
        - Fazer fallback automático em caso de falha
        - Retornar sempre um AIResponse válido
    """

    def __init__(self):
        # Ordem de prioridade dos providers
        self._providers: list[AIProvider] = [
            OpenAIProvider(),
            GroqProvider(),
            GeminiProvider(),
            LocalFallbackProvider(),   # sempre o último
        ]
        self._history: list[ConversationTurn] = []
        self._detector = AIIntentDetector()
        self._active_provider: Optional[AIProvider] = None

        # Resolve o melhor provider disponível na inicialização
        self._resolve_provider()

    def _resolve_provider(self) -> None:
        """Seleciona o primeiro provider disponível e loga a escolha."""
        for provider in self._providers:
            if provider.is_available():
                self._active_provider = provider
                mode = "🟢 Online" if provider.name != "local_fallback" else "🟡 Local"
                logger.info(f"IA: provider selecionado → {provider.name} ({mode})")
                return

    def process(self, text: str) -> AIResponse:
        """
        Processa uma consulta do usuário e retorna um AIResponse.

        Fluxo:
            1. Detecta intenção
            2. Tenta o provider ativo
            3. Em caso de falha, faz fallback para o próximo disponível
            4. Garante retorno mesmo em caso de falha total (defensive programming)
        """
        text = text.strip()
        if not text:
            return AIResponse(
                text="Por favor, diga ou escreva algo.",
                provider="none",
                intent="vazio",
            )

        intent = self._detector.detect(text)
        logger.info(f"IA: texto='{text[:60]}' | intenção={intent} | provider={self._active_provider.name if self._active_provider else 'none'}")

        # Providers a tentar (ativo primeiro, depois os demais como fallback)
        providers_to_try = [self._active_provider] if self._active_provider else []
        providers_to_try += [p for p in self._providers if p is not self._active_provider]

        last_error = None
        for provider in providers_to_try:
            if not provider.is_available():
                continue
            try:
                messages = provider.build_messages(self._history, text, intent)
                reply = provider.complete(messages, intent)
                reply = reply.strip() or "Não consegui gerar uma resposta. Tente novamente."

                # Salva no histórico
                self._history.append(ConversationTurn(role="user",      content=text))
                self._history.append(ConversationTurn(role="assistant",  content=reply))

                # Limita histórico em memória (máx. 30 turnos = 60 itens)
                if len(self._history) > 60:
                    self._history = self._history[-60:]

                return AIResponse(text=reply, provider=provider.name, intent=intent)

            except Exception as e:
                last_error = str(e)
                logger.warning(f"IA: provider {provider.name} falhou: {e}. Tentando próximo...")
                continue

        # Fallback total — nunca deve chegar aqui com LocalFallbackProvider
        logger.error(f"IA: todos os providers falharam. Último erro: {last_error}")
        return AIResponse(
            text="Desculpe, não foi possível processar sua mensagem no momento. Tente novamente.",
            provider="error",
            intent=intent,
            error=last_error,
        )

    def clear_history(self) -> None:
        """Limpa o histórico de conversa."""
        self._history.clear()
        logger.info("IA: histórico de conversa limpo.")

    def get_history(self) -> list[dict]:
        """Retorna o histórico como lista de dicionários."""
        return [{"role": t.role, "content": t.content, "timestamp": t.timestamp}
                for t in self._history]

    def get_info(self) -> dict:
        """Retorna informações sobre o estado atual do motor de IA."""
        available_providers = [p.name for p in self._providers if p.is_available()]
        return {
            "active_provider":      self._active_provider.name if self._active_provider else "none",
            "available_providers":  available_providers,
            "online_mode":          (self._active_provider.name != "local_fallback"
                                     if self._active_provider else False),
            "history_turns":        len(self._history) // 2,
            "version":              config.JARVIS_VERSION,
        }


# ─── Instância Global ─────────────────────────────────────────────────────────
# Singleton que mantém histórico de conversa durante a sessão do servidor.

_engine = AIEngine()


# ─── Interface Pública ────────────────────────────────────────────────────────

def process_query(text: str) -> str:
    """
    Ponto de entrada principal do módulo de IA.

    Detecta automaticamente o melhor provider disponível,
    processa a consulta e retorna a resposta em texto.

    Args:
        text: Texto do usuário (digitado ou reconhecido por voz).

    Returns:
        Resposta em texto pura, pronta para exibir ou sintetizar em voz.

    Exemplo:
        reply = process_query("quais são minhas tarefas hoje?")
        print(reply)
    """
    result = _engine.process(text)
    return result.text


def process_query_detailed(text: str) -> AIResponse:
    """
    Versão de process_query que retorna o AIResponse completo.
    Útil quando você precisa saber qual provider foi usado ou a intenção detectada.
    """
    return _engine.process(text)


def clear_history() -> None:
    """Limpa o histórico de conversa da sessão atual."""
    _engine.clear_history()


def get_ai_info() -> dict:
    """Retorna informações sobre o motor de IA: provider ativo, disponíveis, histórico."""
    return _engine.get_info()


def get_history() -> list[dict]:
    """Retorna o histórico de conversa da sessão atual."""
    return _engine.get_history()


def detect_intent(text: str) -> str:
    """Detecta e retorna a intenção de um texto. Útil para debug e testes."""
    return AIIntentDetector.detect(text)
