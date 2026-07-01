import type { CreateJobResponse, JobResponse, ThumbnailResponse } from './types'

export type ApiClient = {
  uploadHeadshot: (file: File) => Promise<{ url: string }>
  createJob: (input: {
    prompt: string
    num_thumbnails: number
    headshot_url: string
  }) => Promise<CreateJobResponse>
  getJob: (jobId: string) => Promise<JobResponse>
  streamJob: (jobId: string, onEvent: (e: JobStreamEvent) => void) => () => void
}

export type JobStreamEvent =
  | { type: 'thumbnail'; payload: { thumbnail_id: string; style_name: string; imagekit_url: string | null; variants?: any } }
  | { type: 'error'; payload: { error: string } }
  | { type: 'job_complete'; payload: { job_id: string; status: string } }

function getBaseUrl() {
  // Defaults to local backend used by typical setups.
  return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
}

export function createApiClient(): ApiClient {
  const base = getBaseUrl()

  async function uploadHeadshot(file: File) {
    const form = new FormData()
    form.append('file', file)

    const res = await fetch(`${base}/api/upload-headshot`, {
      method: 'POST',
      body: form,
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `Upload failed (${res.status})`)
    }

    return res.json() as Promise<{ url: string }>
  }

  async function createJob(input: {
    prompt: string
    num_thumbnails: number
    headshot_url: string
  }) {
    const res = await fetch(`${base}/api/jobs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    })

    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `Job creation failed (${res.status})`)
    }

    return res.json() as Promise<CreateJobResponse>
  }

  async function getJob(jobId: string) {
    const res = await fetch(`${base}/api/jobs/${encodeURIComponent(jobId)}`)
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || `Failed to load job (${res.status})`)
    }
    return res.json() as Promise<JobResponse>
  }

  function streamJob(jobId: string, onEvent: (e: JobStreamEvent) => void) {
    const controller = new AbortController()

    const url = `${base}/api/jobs/${encodeURIComponent(jobId)}/stream`

    const es = new EventSource(url, { withCredentials: true })

    es.onmessage = () => {}

    es.addEventListener('thumbnail ready', (ev: MessageEvent) => {
      try {
        const payload = JSON.parse(ev.data)
        onEvent({
          type: 'thumbnail',
          payload: payload,
        })
      } catch {
        // ignore
      }
    })

    es.addEventListener('job complete', (ev: MessageEvent) => {
      try {
        const payload = JSON.parse(ev.data)
        onEvent({
          type: 'job_complete',
          payload,
        })
      } catch {
        // ignore
      }
    })

    es.addEventListener('error', (ev: MessageEvent) => {
      try {
        const payload = JSON.parse(ev.data)
        onEvent({ type: 'error', payload })
      } catch {
        onEvent({ type: 'error', payload: { error: 'Stream error' } })
      }
    })

    // Keep it compatible with React unmount
    return () => {
      es.close()
      controller.abort()
    }
  }

  return {
    uploadHeadshot,
    createJob,
    getJob,
    streamJob,
  }
}

