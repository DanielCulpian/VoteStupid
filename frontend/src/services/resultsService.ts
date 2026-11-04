import { apiRequest } from './api'

export interface OptionResult {
  option_id: string
  option_text: string
  votes: number
  points: number
  percentage: number
}

export interface PollResults {
  poll_id: string
  poll_title: string
  total_votes: number
  results: OptionResult[]
}

// Consulta los votos, puntos y porcentajes actuales de una votación.
export function getPollResults(
  pollId: string,
): Promise<PollResults> {
  return apiRequest<PollResults>(
    `/api/polls/${pollId}/results`,
  )
}
