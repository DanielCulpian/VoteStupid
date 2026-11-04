
import { apiRequest } from './api'
import type { PollResponse } from '../types/poll'

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
