import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import Dashboard from './pages/Dashboard'
import Brands from './pages/Brands'
import Monitors from './pages/Monitors'
import Alerts from './pages/Alerts'
import Enrichment from './pages/Enrichment'
import Admin from './pages/Admin'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/brands" element={<Brands />} />
          <Route path="/monitors" element={<Monitors />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/enrichment" element={<Enrichment />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'rgba(18, 18, 26, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#f5f5f5',
          },
        }}
      />
    </QueryClientProvider>
  )
}
