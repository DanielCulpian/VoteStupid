
export type PollType =
  | 'single_choice'
  | 'multiple_choice'
  | 'ranking'

export interface CreatePollRequest {
  title: string
  option_texts: string[]
  poll_type: PollType
  description: string | null
  max_selections: number | null
  closes_at: string | null
}

export interface OptionResponse {
  id: string
  text: string
}

export interface PollResponse {
  id: string
  title: string
  description: string | null
  poll_type: PollType
  options: OptionResponse[]
  max_selections: number | null
  closes_at: string | null
  is_active: boolean
  created_at: string
}
