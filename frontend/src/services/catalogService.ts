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

// Query filters and pagination on the server so older polls are not omitted.
export function getCatalog(state = 'all', type = '', offset = 0, administrative = false) {
  const query = new URLSearchParams({ state, offset: String(offset), limit: '24' })
  if (type) query.set('poll_type', type)
  return apiRequest<PollPage>(`/api/${administrative ? 'admin/' : ''}polls?${query}`)
}

// Account for scheduled closing times when displaying poll availability.
export function isOpen(poll: PollCard, now = Date.now()) {
  return poll.is_active && (!poll.closes_at || Date.parse(poll.closes_at) > now)
}

// Use consistent poll type labels in cards and filters.
export function typeLabel(type: PollType) {
  return { single_choice: 'Elección única', multiple_choice: 'Elección múltiple', ranking: 'Ranking' }[type]
}
