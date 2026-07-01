import React, { useState } from 'react'
import type { ApiClient } from '../api/client'
import type { CreateJobResponse } from '../api/types'

export default function HomePage({
  api,
  onJobCreated,
}: {
  api: ApiClient
  onJobCreated: (res: CreateJobResponse) => void
}) {
  const [prompt, setPrompt] = useState('')
  const [numThumbnails, setNumThumbnails] = useState(3)
  const [headshotFile, setHeadshotFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const styles = [1, 2, 3]

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!prompt.trim()) {
      setError('Enter a prompt')
      return
    }
    if (!headshotFile) {
      setError('Upload a headshot image')
      return
    }

    setBusy(true)
    try {
      const uploadRes = await api.uploadHeadshot(headshotFile)
      const res = await api.createJob({
        prompt,
        num_thumbnails: numThumbnails,
        headshot_url: uploadRes.url,
      })
      onJobCreated(res)
    } catch (err: any) {
      setError(err?.message || 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <h2>Create thumbnails</h2>
      <p className="muted">Describe the style you want. Upload your headshot for reference.</p>

      <form onSubmit={onSubmit} className="form">
        <label className="field">
          <span>Headshot</span>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setHeadshotFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label className="field">
          <span>Prompt</span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Make it bold and dramatic with cinematic lighting..."
            rows={4}
          />
        </label>

        <label className="field">
          <span>Number of thumbnails (1-3)</span>
          <select value={numThumbnails} onChange={(e) => setNumThumbnails(Number(e.target.value))}>
            {styles.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        {error ? <div className="alert">{error}</div> : null}

        <button className="btn" type="submit" disabled={busy}>
          {busy ? 'Creating...' : 'Create'}
        </button>
      </form>
    </div>
  )
}

