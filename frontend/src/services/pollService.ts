import { apiRequest } from './api'
import type {
  CreatePollRequest,
  PollCreatedResponse,
  PollResponse,
} from '../types/poll'

// Create a poll and return its data and administration token.
export function createPoll(
  poll: CreatePollRequest,
): Promise<PollCreatedResponse> {
  return apiRequest<PollCreatedResponse>('/api/polls', {
    method: 'POST',
    body: JSON.stringify(poll),
  })
}

// Retrieve a poll's public data by its identifier.
export function getPoll(pollId: string): Promise<PollResponse> {
  return apiRequest<PollResponse>(`/api/polls/${pollId}`)
}
