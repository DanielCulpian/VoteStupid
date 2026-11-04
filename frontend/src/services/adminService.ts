
import { apiRequest } from './api'
import type { PollResponse } from '../types/poll'

// Obtiene los datos de administración usando el token privado de la votación.
export function getAdminPoll(
  pollId: string,
  adminToken: string,
): Promise<PollResponse> {
  return apiRequest<PollResponse>(
    `/api/admin/polls/${pollId}`,
    {
      headers: {
        'X-Admin-Token': adminToken,
      },
    },
  )
}

// Solicita el cierre de la votación con el token de administración.
export function closePoll(
  pollId: string,
  adminToken: string,
): Promise<PollResponse> {
  return apiRequest<PollResponse>(
    `/api/admin/polls/${pollId}/close`,
    {
      method: 'PUT',
      headers: {
        'X-Admin-Token': adminToken,
      },
    },
  )
}

// Solicita la reapertura de la votación con el token de administración.
export function reopenPoll(
  pollId: string,
  adminToken: string,
): Promise<PollResponse> {
  return apiRequest<PollResponse>(
    `/api/admin/polls/${pollId}/reopen`,
    {
      method: 'PUT',
      headers: {
        'X-Admin-Token': adminToken,
      },
    },
  )
}
