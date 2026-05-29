import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// ==================== 类型定义 ====================

export interface SystemStatus {
  status: string;
  version: string;
  modules_loaded: number;
  generation: number;
  total_interactions: number;
  total_evolutions: number;
  uptime: number;
  start_time: number;
}

export interface ChatResponse {
  answer: string;
  confidence: number;
  domain: string;
  modules_used: string[];
  timestamp: number;
}

export interface ModuleStats {
  [key: string]: Record<string, any>;
}

export interface EvolveResult {
  success: boolean;
  generation: number;
  improvements: number;
  duration: number;
  details: Array<{ type: string; result: any }>;
}

// ==================== API 函数 ====================

export async function getStatus(): Promise<SystemStatus> {
  const { data } = await api.get('/api/status');
  return data;
}

export async function getModules(): Promise<ModuleStats> {
  const { data } = await api.get('/api/modules');
  return data;
}

export async function getModule(moduleId: string): Promise<Record<string, any>> {
  const { data } = await api.get(`/api/modules/${moduleId}`);
  return data;
}

export async function getMemory(): Promise<any> {
  const { data } = await api.get('/api/memory');
  return data;
}

export async function getKnowledge(): Promise<any> {
  const { data } = await api.get('/api/knowledge');
  return data;
}

export async function getReport(): Promise<{ report: string }> {
  const { data } = await api.get('/api/report');
  return data;
}

export async function getHealth(): Promise<any> {
  const { data } = await api.get('/api/health');
  return data;
}

export async function getProviders(): Promise<any> {
  const { data } = await api.get('/api/providers');
  return data;
}

export async function chat(message: string, provider: string = 'local'): Promise<ChatResponse> {
  const { data } = await api.post('/api/chat', { message, provider });
  return data;
}

export async function chatStream(
  message: string,
  onChunk: (chunk: string) => void,
  onDone: (result: any) => void,
  onError?: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, stream: true }),
    });

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No reader');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (data.done) {
            onDone(data);
          } else {
            onChunk(data.chunk);
          }
        }
      }
    }
  } catch (error) {
    onError?.(error as Error);
  }
}

export async function learn(content: string, source: string = 'user'): Promise<any> {
  const { data } = await api.post('/api/learn', { content, source });
  return data;
}

export async function evolve(trigger: string = 'manual'): Promise<EvolveResult> {
  const { data } = await api.post('/api/evolve', { trigger });
  return data;
}

export async function setGoal(goal: string, priority: string = 'medium'): Promise<any> {
  const { data } = await api.post('/api/goal', { goal, priority });
  return data;
}

export async function getGoals(): Promise<any> {
  const { data } = await api.get('/api/goals');
  return data;
}

export default api;
