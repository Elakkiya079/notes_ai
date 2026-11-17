import { NavLink, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

export default function Sidebar() {
  const { user, setUser, config } = useAuth();
  const navigate = useNavigate();

  async function logout() {
    await api('/api/auth/logout', { method: 'POST' });
    setUser(null);
    navigate('/');
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="mark" aria-hidden="true">N</span>
        <div>
          <strong>Notes</strong>
          <p>Study documents</p>
        </div>
      </div>
      <nav className="side-nav">
        <NavLink to="/notes" className={({ isActive }) => (isActive ? 'active' : undefined)}>Notes</NavLink>
        <NavLink to="/import" className={({ isActive }) => (isActive ? 'active' : undefined)}>Import</NavLink>
      </nav>
      <div className="side-github">
        {user?.github ? (
          <p>GitHub connected as <strong>{user.github.username}</strong></p>
        ) : config?.github ? (
          <a href="/api/auth/github">Connect GitHub</a>
        ) : (
          <p>Add GitHub OAuth keys to read private repositories. Public repository URLs still work.</p>
        )}
      </div>
      <div className="side-foot">
        <ThemeToggle />
        <div className="account">
          {user?.avatar ? <img src={user.avatar} alt="" /> : <span className="avatar-fallback">{(user?.name || 'N').slice(0, 1)}</span>}
          <div>
            <strong>{user?.name}</strong>
            <button type="button" onClick={logout}>Log out</button>
          </div>
        </div>
      </div>
    </aside>
  );
}
