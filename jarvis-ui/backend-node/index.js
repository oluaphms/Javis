// d:\JAVIS\jarvis-ui\backend-node\index.js
const path = require('path');
// Raiz do repo e pasta deste backend (a chave costuma estar só em um dos .env)
require('dotenv').config({ path: path.join(__dirname, '..', '..', '.env') });
require('dotenv').config({ path: path.join(__dirname, '.env'), override: true });
require('dotenv').config({ path: path.join(__dirname, '..', '..', 'backend', '.env'), override: true });

// Tratamento de Erros Fatal para diagnóstico no Windows
process.on('uncaughtException', (err) => {
    console.error('\n❌ ERRO CRÍTICO NO BACKEND:\n', err);
});
process.on('unhandledRejection', (reason, promise) => {
    console.error('\n❌ PROMESSA REJEITADA NÃO TRATADA:\n', reason);
});

const express = require('express');
const cors = require('cors');
const { exec } = require('child_process');
const { GoogleGenerativeAI } = require("@google/generative-ai");

const app = express();
app.use(cors());
app.use(express.json());

// ─── Configuração do Gemini ──────────────────────────────────────────────────
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-1.5-flash";
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "");
const model = genAI.getGenerativeModel({ model: GEMINI_MODEL });

/**
 * Modo sem GEMINI_API_KEY: respostas úteis (sem frase fixa de “processando…”).
 */
function localModeReply(rawText) {
    const t = rawText.toLowerCase().trim();
    const localResponses = {
        oi: ["Olá! Como posso ajudar você hoje?", "Oi! Em que posso ajudar?", "Olá! Jarvis online."],
        olá: ["Oi! Como vai?", "Saudações!"],
        "quem é você": ["Sou o Jarvis, seu assistente neste PC. No modo local respondo por regras; com GEMINI_API_KEY no .env ganho conversa completa."],
        ajuda: [
            "Posso abrir Chrome, VS Code, calculadora e mais (digite “abrir chrome”). Para respostas inteligentes a qualquer pergunta, adicione GEMINI_API_KEY no .env.",
        ],
        status: ["Jarvis 2.0 no ar. Modo local ativo até você configurar a chave Gemini.", "Sistema estável."],
        tchau: ["Até mais!", "Tchau!"],
        obrigado: ["Disponha!", "Sempre às ordens!"],
    };

    const randomReply = (arr) => arr[Math.floor(Math.random() * arr.length)];
    for (const key of Object.keys(localResponses)) {
        if (t.includes(key)) return randomReply(localResponses[key]);
    }

    // Perguntas abertas: explicar limite + dica (em vez de resposta genérica vazia)
    if (/\b(como|por que|porque|o que|qual|quando|onde|explique|defina|significa)\b/.test(t) || t.includes("?")) {
        return "Sem chave de IA (GEMINI_API_KEY no .env), não consigo raciocinar sobre isso aqui. Obtenha uma chave em Google AI Studio e reinicie o backend, ou use comandos como “abrir chrome”.";
    }

    const snippets = [
        `Sobre “${rawText.slice(0, 120)}${rawText.length > 120 ? "…" : ""}”: no modo local só reconheço cumprimentos, ajuda e comandos. Para conversar de verdade, coloque GEMINI_API_KEY em .env (raiz do projeto ou jarvis-ui/backend-node).`,
        "Posso executar coisas no Windows: experimente dizer “abrir chrome” ou “abrir vscode”.",
        "Se quiser respostas livres às suas perguntas, configure GEMINI_API_KEY e reinicie o servidor.",
        "Estou ouvindo. No modo atual uso regras locais; com Gemini configurado respondo a qualquer assunto.",
    ];
    return snippets[Math.floor(Math.random() * snippets.length)];
}

// ─── Motor de Comandos Windows ───────────────────────────────────────────────
const systemCommands = {
    "abrir chrome": "start chrome",
    "abrir vscode": "code",
    "bloquear tela": "rundll32.exe user32.dll,LockWorkStation",
    "calculadora": "calc",
    "gerenciador de tarefas": "taskmgr"
};

// ─── Rotas ───────────────────────────────────────────────────────────────────

// Rota de Status (Usada pelo Head do Jarvis no React)
app.get('/api/jarvis/status', (req, res) => {
    res.json({ status: "online", version: "2.0 (Node)" });
});

// Rota de Resumo de Tarefas (Stub para não quebrar a UI)
app.get('/api/tasks/summary', (req, res) => {
    res.json({
        total: 0,
        pendentes: 0,
        em_progresso: 0,
        concluidas: 0,
    });
});

app.get(['/api/tasks', '/api/tasks/'], (req, res) => {
    res.json([]);
});

function buildGeminiUserContent(text, systemPrompt, skills) {
    const parts = [];
    if (skills && String(skills).trim()) {
        parts.push("Contexto e skills indicados pelo usuário:\n" + String(skills).trim());
    }
    if (systemPrompt && String(systemPrompt).trim()) {
        parts.push("Instruções permanentes (persona e regras):\n" + String(systemPrompt).trim());
    }
    parts.push("Pedido atual:\n" + String(text).trim());
    return parts.join("\n\n---\n\n");
}

// A Rota Principal de Query do Jarvis
app.post('/api/jarvis/query', async (req, res) => {
    const { text, system_prompt: systemPrompt, skills } = req.body;
    if (!text) return res.status(400).json({ reply: "Diga algo, mestre." });

    const t = text.toLowerCase();

    // 1. TENTAR COMANDOS DE SISTEMA LOCAL
    for (const key in systemCommands) {
        if (t.includes(key)) {
            console.log(`[Jarvis] Executando comando: ${key}`);
            exec(systemCommands[key]);
            return res.json({ reply: `Com certeza. Executando ${key} agora para você!` });
        }
    }

    // 2. FALLBACK PARA O GEMINI (IA) OU LOCAL
    try {
        if (!process.env.GEMINI_API_KEY) {
            console.log("USANDO FALLBACK LOCAL (defina GEMINI_API_KEY no .env para IA completa)");
            return res.json({ reply: localModeReply(text) });
        }

        console.log("USANDO GEMINI");
        const hasContext =
            (systemPrompt && String(systemPrompt).trim()) || (skills && String(skills).trim());
        const userBlock = hasContext
            ? buildGeminiUserContent(text, systemPrompt || "", skills || "")
            : String(text).trim();
        const result = await model.generateContent(
            `Você é o assistente Jarvis. Responda em português do Brasil, de forma natural e útil, em poucas frases quando couber.\n\n${userBlock}`
        );
        const response = result.response.text();
        return res.json({ reply: response });
    } catch (e) {
        console.error("Erro no Processamento:", e);
        const hint =
            process.env.GEMINI_API_KEY &&
            " Verifique GEMINI_MODEL e se a chave é válida; tente gemini-1.5-flash em GEMINI_MODEL.";
        return res.json({
            reply: `Não consegui processar isso agora.${hint || " Configure GEMINI_API_KEY no .env para usar a IA."}`,
        });
    }
});

// ─── Rota TTS (ElevenLabs opcional) ──────────────────────────────────────────
app.post('/api/tts', async (req, res) => {
    const { text } = req.body;
    const apiKey = process.env.ELEVENLABS_API_KEY;
    const voiceId = process.env.ELEVENLABS_VOICE_ID || "pNInz6ovfV9PZ3jd7Lsr"; // Voz padrão

    if (!text) return res.status(400).json({ error: "Texto vazio" });

    if (!apiKey) {
        console.log("[TTS] Chave ElevenLabs ausente. Usando fallback local.");
        return res.status(501).json({ error: "ElevenLabs API Key não configurada no .env" });
    }

    try {
        const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
            method: "POST",
            headers: {
                "xi-api-key": apiKey,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                model_id: "eleven_multilingual_v2",
                voice_settings: { stability: 0.5, similarity_boost: 0.8 }
            })
        });

        if (!response.ok) throw new Error(`ElevenLabs respondeu com ${response.status}`);

        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);
        
        res.set({
            'Content-Type': 'audio/mpeg',
            'Content-Length': buffer.length
        });
        res.send(buffer);
    } catch (e) {
        console.error("Erro TTS ElevenLabs:", e);
        res.status(500).json({ error: "Falha ao gerar áudio" });
    }
});

// Inicia o Servidor
const PORT = 8008;
app.listen(PORT, () => {
    console.log(`\n🚀 J.A.R.V.I.S — Cérebro Node.js Online`);
    console.log(`📡 Ouvindo em http://localhost:${PORT}/api`);
    console.log(`🔧 Controle do Windows Habilitado`);
    if (process.env.GEMINI_API_KEY) {
        console.log(`🧠 Gemini ativo (modelo: ${GEMINI_MODEL})\n`);
    } else {
        console.log(`⚠️  Sem GEMINI_API_KEY — só modo local + comandos. Coloque a chave no .env da raiz ou jarvis-ui/backend-node\n`);
    }
});
