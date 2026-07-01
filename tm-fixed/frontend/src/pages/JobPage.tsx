import React, { useEffect, useMemo, useState } from 'react'
import type { ApiClient, JobStreamEvent } from '../api/client'
import type { JobResponse, ThumbnailResponse } from '../api/types'

export default function JobPage({
  api,
  jobId,
  onDone,
}: {
  api: ApiClient
  jobId: string
  onDone: () => void
}) {
  const [job, setJob] = useState<JobResponse | null>(null)
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const thumbnailsById = useMemo(() => {
    const map = new Map<string, ThumbnailResponse>()
    for (const t of job?.thumbnails ?? []) map.set(t.id, t)
    return map
  }, [job])

  useEffect(() => {
    let unbind: null | (() => void) = null

    ;(async () => {
      try {
        const initial = await api.getJob(jobId)
        setJob(initial)
        setBusy(
          initial.status === 'pending' ||
            initial.status === 'processing' ||
            initial.status === 'generating',
        )
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load job')
      }

      unbind = api.streamJob(jobId, (ev: JobStreamEvent) => {
        if (ev.type === 'thumbnail') {
          setJob((prev) => {
            if (!prev) return prev
            const next: JobResponse = { ...prev, thumbnails: [...prev.thumbnails] }
            // Explicit type on `t` to satisfy strict TypeScript
            const existing = next.thumbnails.find(
              (t: ThumbnailResponse) => t.id === ev.payload.thumbnail_id,
            )
            if (existing) {
              existing.imagekit_url = ev.payload.imagekit_url
              existing.status = 'uploaded'
              existing.variants = ev.payload.variants
            }
            return next
          })
        }

        if (ev.type === 'error') {
          setError(ev.payload.error)
        }

        if (ev.type === 'job_complete') {
          setBusy(false)
          api
            .getJob(jobId)
            .then(setJob)
            .catch(() => {})
        }
      })
    })()

    return () => {
      if (unbind) unbind()
    }
  }, [api, jobId])

  const status = job?.status ?? 'loading'

  return (
    <div className="card">
      <div className="row row--between">
        <h2>Job</h2>
        <button className="btn btn--ghost" onClick={onDone}>
          New job
        </button>
      </div>

      <div className="muted">Job ID: {jobId}</div>
      <div className="status">Status: {status}</div>

      {error ? <div className="alert">{error}</div> : null}

      {!job ? (
        <div className="spinner">Waiting for thumbnails…</div>
      ) : (
        <div className="grid">
          {job.thumbnails.map((t) => (
            <div key={t.id} className="thumb">
              <div className="thumb__meta">
                <div className="thumb__style">{t.style_name}</div>
                <div className="pill">{t.status}</div>
              </div>

              {t.status === 'failed' ? (
                <div className="thumb__error">{t.error_message || 'Failed'}</div>
              ) : null}

              {t.imagekit_url ? (
                <div className="thumb__imgWrap">
                  <img className="thumb__img" src={t.imagekit_url} alt={t.style_name} />
                </div>
              ) : (
                <div className="thumb__placeholder">
                  {t.status === 'generating' ? 'Generating…' : 'No image yet'}
                </div>
              )}

              {t.variants ? (
                <div className="variants">
                  <a className="variantLink" href={t.variants.youtube} target="_blank" rel="noreferrer">
                    YouTube (1280×720)
                  </a>
                  <a className="variantLink" href={t.variants.shorts} target="_blank" rel="noreferrer">
                    Shorts (1080×1920)
                  </a>
                  <a className="variantLink" href={t.variants.square} target="_blank" rel="noreferrer">
                    Square (1080×1080)
                  </a>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {busy ? <div className="muted">Generating…</div> : <div className="muted">Done.</div>}
    </div>
  )
}
