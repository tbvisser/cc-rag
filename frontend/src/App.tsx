import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { AuthGuard } from '@/components/auth/AuthGuard'
import { AppLayout } from '@/components/layout/AppLayout'
import Login from '@/pages/Login'
import Signup from '@/pages/Signup'
import Home from '@/pages/Home'
import ChatView from '@/pages/ChatView'
import SchemaManagement from '@/pages/SchemaManagement'
import PlaceholderPage from '@/pages/PlaceholderPage'
import Settings from '@/pages/Settings'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route
          element={
            <AuthGuard>
              <AppLayout />
            </AuthGuard>
          }
        >
          <Route index element={<Home />} />
          <Route path="chat" element={<ChatView />} />
          <Route path="chat/:threadId" element={<ChatView />} />
          <Route path="schema/upload" element={<SchemaManagement />} />
          <Route path="supply-chain/*" element={<PlaceholderPage />} />
          <Route path="industry/*" element={<PlaceholderPage />} />
          <Route path="context/*" element={<PlaceholderPage />} />
          <Route path="graph/*" element={<PlaceholderPage />} />
          <Route path="schema/download" element={<PlaceholderPage />} />
          <Route path="schema/reset" element={<PlaceholderPage />} />
          <Route path="account" element={<PlaceholderPage />} />
          <Route path="settings" element={<Settings />} />
          <Route path="about" element={<PlaceholderPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
