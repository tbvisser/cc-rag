export interface Thread {
  id: string
  title: string | null
  created_at: string
}

export interface Attachment {
  type: string
  url: string
  storage_path?: string
  alt?: string
  label?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  attachments?: Attachment[]
  created_at: string
}
