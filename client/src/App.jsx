import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import RequireAuth from './components/RequireAuth';
import ImportPage from './pages/Import';
import Login from './pages/Login';
import Notes from './pages/Notes';
import Review from './pages/Review';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route element={<AppLayout />}>
          <Route path="/notes" element={<Notes />} />
          <Route path="/notes/:folderSlug" element={<Notes />} />
          <Route path="/notes/:folderSlug/:noteId" element={<Notes />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/import/:jobId" element={<Review />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
