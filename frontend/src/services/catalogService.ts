import { apiRequest } from './api'
import type { PollType } from '../types/poll'

export interface PollCard {
  id: string
  title: string
  description: string | null
  poll_type: PollType
  created_at: string
  is_active: boolean
  closes_at: string | null
}
export interface PollPage { items: PollCard[]; total: number; offset: number; limit: number }

// Consulta filtros y paginación en el servidor para no omitir votaciones antiguas.
export function getCatalog(state = 'all', type = '', offset = 0, administrative = false) {
  const query = new URLSearchParams({ state, offset: String(offset), limit: '24' })
  if (type) query.set('poll_type', type)
  return apiRequest<PollPage>(`/api/${administrative ? 'admin/' : ''}polls?${query}`)
}

// Considera también la fecha programada al mostrar la disponibilidad de una votación.
export function isOpen(poll: PollCard, now = Date.now()) {
  return poll.is_active && (!poll.closes_at || Date.parse(poll.closes_at) > now)
}

// Presenta los tipos con la misma denominación en tarjetas y filtros.
export function typeLabel(type: PollType) {
  return { single_choice: 'Elección única', multiple_choice: 'Elección múltiple', ranking: 'Ranking' }[type]
}
