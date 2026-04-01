/**
 * Prompt do sistema, skills/contexto e gênero da voz (TTS).
 * Persistido em localStorage.
 */

import React, { createContext, useContext, useState, useEffect, useMemo } from "react";

const LS = {
  systemPrompt: "jarvis_system_prompt",
  skills: "jarvis_skills",
  voiceGender: "jarvis_voice_gender",
};

const JarvisSettingsContext = createContext(null);

export function JarvisSettingsProvider({ children }) {
  const [systemPrompt, setSystemPrompt] = useState(
    () => localStorage.getItem(LS.systemPrompt) || ""
  );
  const [skills, setSkills] = useState(() => localStorage.getItem(LS.skills) || "");
  const [voiceGender, setVoiceGender] = useState(
    () => localStorage.getItem(LS.voiceGender) || "auto"
  );

  useEffect(() => {
    localStorage.setItem(LS.systemPrompt, systemPrompt);
  }, [systemPrompt]);

  useEffect(() => {
    localStorage.setItem(LS.skills, skills);
  }, [skills]);

  useEffect(() => {
    localStorage.setItem(LS.voiceGender, voiceGender);
  }, [voiceGender]);

  const value = useMemo(
    () => ({
      systemPrompt,
      setSystemPrompt,
      skills,
      setSkills,
      voiceGender,
      setVoiceGender,
    }),
    [systemPrompt, skills, voiceGender]
  );

  return (
    <JarvisSettingsContext.Provider value={value}>{children}</JarvisSettingsContext.Provider>
  );
}

export function useJarvisSettings() {
  const ctx = useContext(JarvisSettingsContext);
  if (!ctx) {
    throw new Error("useJarvisSettings deve estar dentro de JarvisSettingsProvider");
  }
  return ctx;
}
