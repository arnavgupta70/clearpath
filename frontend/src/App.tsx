import { useEffect, useState, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { isReviewer, PersonaProvider, useMeta, usePersona } from './lib/persona'
import { Insights } from './pages/Insights'
import { Login } from './pages/Login'
import { MySubmissions } from './pages/MySubmissions'
import { NewSubmission } from './pages/NewSubmission'
import { Queue } from './pages/Queue'
import { Review } from './pages/Review'
import { SubmissionDetail } from './pages/SubmissionDetail'

export function App() {
  const meta = useMeta()
  if (meta.error) return <p className="p-8 text-center">Couldn't reach the API. <button onClick={() => meta.refetch()} className="text-brand underline">Try again</button></p>
  if (!meta.data) return <WakingUp />

  return (
    <PersonaProvider meta={meta.data}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/queue" element={<ReviewerOnly><Queue /></ReviewerOnly>} />
          <Route path="/review/:id" element={<ReviewerOnly><Review /></ReviewerOnly>} />
          <Route path="/insights" element={<ReviewerOnly><Insights /></ReviewerOnly>} />
          <Route path="/submissions" element={<SubmitterOnly><MySubmissions /></SubmitterOnly>} />
          <Route path="/submissions/new" element={<SubmitterOnly><NewSubmission /></SubmitterOnly>} />
          <Route path="/submissions/:id" element={<SubmitterOnly><SubmissionDetail /></SubmitterOnly>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </PersonaProvider>
  )
}

function Home() {
  const { user } = usePersona()
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={isReviewer(user) ? '/queue' : '/submissions'} replace />
}

function ReviewerOnly({ children }: { children: ReactNode }) {
  const { user } = usePersona()
  return user && isReviewer(user) ? children : <Navigate to="/" replace />
}

function SubmitterOnly({ children }: { children: ReactNode }) {
  const { user } = usePersona()
  return user && !isReviewer(user) ? children : <Navigate to="/" replace />
}

// the free API host sleeps when idle, so say so if the first request is slow
function WakingUp() {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 2500)
    return () => clearTimeout(timer)
  }, [])
  return <p className="p-8 text-center text-ink-2">{slow ? 'Waking up the server, this can take up to a minute…' : 'Loading…'}</p>
}
