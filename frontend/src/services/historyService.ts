import type { PollResponse, PollType } from '../types/poll'

const HISTORY_KEY = 'votestupid:created-polls:v1'
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export interface PollHistoryEntry {
  id: string
  title: string
  poll_type: PollType
  created_at: string
  is_active: boolean
  closes_at: string | null
}

// Valida los datos locales y conserva únicamente metadatos públicos, nunca tokens ni enlaces privados.
function historyEntry(value: unknown): PollHistoryEntry | null {
  if (typeof value !== 'object' || value === null) return null
  const item = value as Record<string, unknown>
  if (
    typeof item.id !== 'string' || !UUID_PATTERN.test(item.id) ||
    typeof item.title !== 'string' || !item.title.trim() ||
    !['single_choice', 'multiple_choice', 'ranking'].includes(String(item.poll_type)) ||
    typeof item.created_at !== 'string' || !Number.isFinite(Date.parse(item.created_at)) ||
    typeof item.is_active !== 'boolean'
  ) return null

  return {
    id: item.id.toLowerCase(),
    title: item.title,
    poll_type: item.poll_type as PollType,
    created_at: item.created_at,
    is_active: item.is_active,
    closes_at: typeof item.closes_at === 'string' && Number.isFinite(Date.parse(item.closes_at))
      ? item.closes_at
      : null,
  }
}

// Lee las votaciones recordadas por este navegador, sin consultar ni enumerar las de otros usuarios.
export function getPollHistory(): PollHistoryEntry[] {
  try {
    const stored = localStorage.getItem(HISTORY_KEY)
    if (!stored) return []
    const parsed: unknown = JSON.parse(stored)
    if (!Array.isArray(parsed)) throw new Error('Formato de histórico incorrecto.')
    const entries = new Map<string, PollHistoryEntry>()
    for (const item of parsed) {
      const entry = historyEntry(item)
      if (entry && !entries.has(entry.id)) entries.set(entry.id, entry)
    }
    return [...entries.values()].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
  } catch {
    throw new Error('No se puede leer el histórico de este navegador. Tus votaciones siguen en el servidor y puedes recuperarlas con sus enlaces privados.')
  }
}

// Guarda o actualiza una votación con una lista explícita de campos públicos y sin duplicar entradas.
export function rememberPoll(poll: PollResponse): void {
  const entry = historyEntry(poll)
  if (!entry) throw new Error('No se han podido reconocer los datos de la votación para guardarla en el histórico.')
  const entries = getPollHistory().filter(item => item.id !== entry.id)
  entries.push(entry)
  entries.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries))
  } catch {
    throw new Error('No se ha podido guardar el histórico en este navegador. Guarda los enlaces de tu votación para recuperarla después.')
  }
}

// Indica si esta pestaña conserva una credencial; el backend seguirá validándola al abrir la administración.
export function hasSessionAdminAccess(pollId: string): boolean {
  try {
    return Boolean(sessionStorage.getItem(`votestupid:admin-token:${pollId}`)?.trim())
  } catch {
    return false
  }
}

// Extrae el identificador y el token de un enlace privado de esta aplicación sin enviarlo a otros dominios.
export function parsePrivatePollLink(link: string, origin: string): { id: string; token: string } {
  try {
    const url = new URL(link.trim(), origin)
    const match = url.pathname.match(/^\/admin\/([0-9a-f-]+)\/?$/i)
    const token = new URLSearchParams(url.hash.slice(1)).get('token')
    if (url.origin !== origin || !match?.[1] || !UUID_PATTERN.test(match[1]) || !token?.trim()) {
      throw new Error('Enlace incorrecto.')
    }
    return { id: match[1].toLowerCase(), token }
  } catch {
    throw new Error('Introduce el enlace privado completo de esta aplicación, incluido su token de administración.')
  }
}
