import { apiRequest } from './api'
import type { CreatePollRequest, PollResponse } from '../types/poll'

export function createPoll(
  poll: CreatePollRequest,
): Promise<PollResponse> {
  return apiRequest<PollResponse>('/api/polls', {
    method: 'POST',
    body: JSON.stringify(poll),
  })
}

export function getPoll(pollId: string): Promise<PollResponse> {
  return apiRequest<PollResponse>(`/api/polls/${pollId}`)
}
