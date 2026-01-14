import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { Layout } from './components/Layout';
import { AuthGate } from './components/AuthGate';
import { TermsGate } from './components/TermsGate';
import { Home } from './pages/Home';
import { Privacy } from './pages/Privacy';
import { Terms } from './pages/Terms';
import { Accept } from './pages/Accept';
import { Login } from './pages/Login';
import { LoginCallback } from './pages/LoginCallback';
import { AppHome } from './pages/app/AppHome';
import { Connect } from './pages/app/Connect';
import { Welcome } from './pages/app/Welcome';
import { Insights } from './pages/app/Insights';
import { MetricDetail } from './pages/app/MetricDetail';
import { Chat } from './pages/app/Chat';

function App() {
  return (
    <AuthProvider>
      <Layout>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Home />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/accept" element={<Accept />} />
          <Route path="/login" element={<Login />} />
          <Route path="/login/callback" element={<LoginCallback />} />

          {/* Protected app routes - require auth first, then terms acceptance */}
          <Route
            path="/app"
            element={
              <AuthGate>
                <TermsGate>
                  <AppHome />
                </TermsGate>
              </AuthGate>
            }
          />
          <Route
            path="/app/connect"
            element={
              <AuthGate>
                <TermsGate>
                  <Connect />
                </TermsGate>
              </AuthGate>
            }
          />
          <Route
            path="/app/welcome"
            element={
              <AuthGate>
                <TermsGate>
                  <Welcome />
                </TermsGate>
              </AuthGate>
            }
          />
          <Route
            path="/app/insights"
            element={
              <AuthGate>
                <TermsGate>
                  <Insights />
                </TermsGate>
              </AuthGate>
            }
          />
          <Route
            path="/app/insights/:metric"
            element={
              <AuthGate>
                <TermsGate>
                  <MetricDetail />
                </TermsGate>
              </AuthGate>
            }
          />
          <Route
            path="/app/chat"
            element={
              <AuthGate>
                <TermsGate>
                  <Chat />
                </TermsGate>
              </AuthGate>
            }
          />
        </Routes>
      </Layout>
    </AuthProvider>
  );
}

export default App;
