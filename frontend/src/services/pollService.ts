import { apiRequest } from './api'
import type {
  CreatePollRequest,
  PollCreatedResponse,
  PollResponse,
} from '../types/poll'

export function createPoll(
  poll: CreatePollRequest,
): Promise<PollCreatedResponse> {
  return apiRequest<PollCreatedResponse>('/api/polls', {
    method: 'POST',
    body: JSON.stringify(poll),
  })
}

export function getPoll(pollId: string): Promise<PollResponse> {
  return apiRequest<PollResponse>(`/api/polls/${pollId}`)
}
