import { apiRequest } from './api'
import type {
  CreatePollRequest,
  PollCreatedResponse,
  PollResponse,
} from '../types/poll'

// Crea una votación y devuelve sus datos junto con el token de administración.
export function createPoll(
  poll: CreatePollRequest,
): Promise<PollCreatedResponse> {
  return apiRequest<PollCreatedResponse>('/api/polls', {
    method: 'POST',
    body: JSON.stringify(poll),
  })
}

// Obtiene los datos públicos de una votación por su identificador.
export function getPoll(pollId: string): Promise<PollResponse> {
  return apiRequest<PollResponse>(`/api/polls/${pollId}`)
}
