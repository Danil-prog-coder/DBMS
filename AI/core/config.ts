import { ollama } from 'ollama-ai-provider';
import type { Config } from 'opencoder';

export default {
  // Указываем, что используем локальную модель через Ollama
  model: ollama('qwen2.5-coder:7b'),

  // Дополнительные настройки (по желанию)
  systemPrompt: "Ты - опытный программист, помогающий писать чистый и эффективный код.",
  maxTokens: 4096,
} satisfies Config;