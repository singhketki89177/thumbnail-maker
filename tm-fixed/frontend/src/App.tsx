import React, { useMemo, useState } from 'react'
import { createApiClient, type ApiClient } from './api/client'
import type { CreateJobResponse, JobResponse, ThumbnailResponse } from './api/types'
import HomePage from './pages/HomePage'
import JobPage from './pages/JobPage'

export type ViewState =
  | { view: 'home' }
  | { view: 'job'; jobId: string }

export default function App() {
  const api = useMemo<ApiClient>(() => createApiClient(), [])
  const [view, setView] = useState<ViewState>({ view: 'home' })

  const goHome = () => setView({ view: 'home' })

  const onJobCreated = (res: CreateJobResponse) => {
    setView({ view: 'job', jobId: res.job_id })
  }

  const renderJob = (jobId: string) => {
    return <JobPage api={api} jobId={jobId} onDone={goHome} />
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header__brand">Thumbnail Generator</div>
      </header>

      <main className="container">
        {view.view === 'home' ? (
          <HomePage api={api} onJobCreated={onJobCreated} />
        ) : (
          renderJob(view.jobId)
        )}
      </main>

      <footer className="footer">
        <span>Built with React + Vite</span>
      </footer>
    </div>
  )
}

