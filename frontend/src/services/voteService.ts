
import { apiRequest } from './api'

export interface VoteResponse {
  id: string
  poll_id: string
  selected_option_ids: string[]
  created_at: string
  updated_at: string
}

// Retrieve the participant's local token, or generate and store one for this poll.
function getVoterToken(pollId: string): string {
  const storageKey = `votestupid:voter-token:${pollId}`

  let token = localStorage.getItem(storageKey)

  if (!token) {
    const randomBytes = crypto.getRandomValues(new Uint8Array(32))

    token = Array.from(randomBytes)
      .map(byte => byte.toString(16).padStart(2, '0'))
      .join('')

    localStorage.setItem(storageKey, token)
  }

  return token
}

// Submit the participant's selection using their local token.
export function castVote(
  pollId: string,
  selectedOptionIds: string[],
): Promise<VoteResponse> {
  return apiRequest<VoteResponse>(`/api/polls/${pollId}/votes`, {
    method: 'POST',
    headers: {
      'X-Voter-Token': getVoterToken(pollId),
    },
    body: JSON.stringify({
      selected_option_ids: selectedOptionIds,
    }),
  })
}

// Update the vote selection associated with the participant's local token.
export function updateVote(
  pollId: string,
  selectedOptionIds: string[],
): Promise<VoteResponse> {
  return apiRequest<VoteResponse>(`/api/polls/${pollId}/votes`, {
    method: 'PUT',
    headers: {
      'X-Voter-Token': getVoterToken(pollId),
    },
    body: JSON.stringify({
      selected_option_ids: selectedOptionIds,
    }),
  })
}
