import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { TermsGate } from './components/TermsGate';
import { Home } from './pages/Home';
import { Privacy } from './pages/Privacy';
import { Terms } from './pages/Terms';
import { Accept } from './pages/Accept';
import { AppHome } from './pages/app/AppHome';
import { Connect } from './pages/app/Connect';
import { Welcome } from './pages/app/Welcome';

function App() {
  return (
    <Layout>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Home />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/accept" element={<Accept />} />

        {/* Protected app routes - require terms acceptance */}
        <Route
          path="/app"
          element={
            <TermsGate>
              <AppHome />
            </TermsGate>
          }
        />
        <Route
          path="/app/connect"
          element={
            <TermsGate>
              <Connect />
            </TermsGate>
          }
        />
        <Route
          path="/app/welcome"
          element={
            <TermsGate>
              <Welcome />
            </TermsGate>
          }
        />
      </Routes>
    </Layout>
  );
}

export default App;
