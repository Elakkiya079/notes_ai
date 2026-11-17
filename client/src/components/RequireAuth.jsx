import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function RequireAuth() {
  const { user } = useAuth();
  if (user === undefined) return <div className="splash">Opening notes…</div>;
  if (!user) return <Navigate to="/" replace />;
  return <Outlet />;
}
