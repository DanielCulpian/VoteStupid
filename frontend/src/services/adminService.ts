
import { apiRequest } from './api'
import type { PollResponse } from '../types/poll'

// Retrieve administrative poll data using the session and optional private token.
export function getAdminPoll(
  pollId: string,
  adminToken = '',
): Promise<PollResponse> {
  return apiRequest<PollResponse>(
    `/api/admin/polls/${pollId}`,
    {
      headers: {
        ...(adminToken ? { 'X-Admin-Token': adminToken } : {}),
      },
    },
  )
}

// Request poll closure with the session and optional administration token.
export function closePoll(
  pollId: string,
  adminToken = '',
): Promise<PollResponse> {
  return apiRequest<PollResponse>(
    `/api/admin/polls/${pollId}/close`,
    {
      method: 'PUT',
      headers: {
        ...(adminToken ? { 'X-Admin-Token': adminToken } : {}),
      },
    },
  )
}

// Request poll reopening with the session and optional administration token.
export function reopenPoll(
  pollId: string,
  adminToken = '',
): Promise<PollResponse> {
  return apiRequest<PollResponse>(
    `/api/admin/polls/${pollId}/reopen`,
    {
      method: 'PUT',
      headers: {
        ...(adminToken ? { 'X-Admin-Token': adminToken } : {}),
      },
    },
  )
}
