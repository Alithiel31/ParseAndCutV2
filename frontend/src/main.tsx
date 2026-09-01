import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import App from './App.tsx'
import Home from './pages/Home.tsx'
import Cgu from './pages/Cgu.tsx'
import Confidentialite from './pages/Confidentialite.tsx'
import MentionsLegales from './pages/MentionsLegales.tsx'
import NotFound from './pages/NotFound.tsx'
import { LanguageProvider } from './i18n'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          {/* App sert de layout : header, footer et bannière de mise à jour communs */}
          <Route element={<App />}>
            <Route index element={<Home />} />
            <Route path="cgu" element={<Cgu />} />
            <Route path="politique-de-confidentialite" element={<Confidentialite />} />
            <Route path="mentions-legales" element={<MentionsLegales />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LanguageProvider>
  </StrictMode>,
)
