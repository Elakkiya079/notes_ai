import { useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import ThemeToggle from '../components/ThemeToggle';
import { useAuth } from '../context/AuthContext';

const AUTH_MESSAGES = {
  google_not_configured: 'Google sign-in is not configured on the server yet.',
  google_denied: 'Google sign-in was cancelled.',
  google_error: 'Google sign-in did not finish. Check the OAuth client and try again.',
  github_error: 'GitHub could not be connected.',
};

export default function Login() {
  const { user, config, error, setUser, refresh } = useAuth();
  const [params] = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState('');
  const navigate = useNavigate();
  const authMessage = AUTH_MESSAGES[params.get('auth')] || '';

  if (user === undefined) {
    return (
      <div className="splash">
        <ThemeToggle />
        <p>Opening notes…</p>
      </div>
    );
  }
  if (user) return <Navigate to="/notes" replace />;

  async function preview() {
    setBusy(true);
    setFormError('');
    try {
      const data = await api('/api/auth/dev', { method: 'POST', body: {} });
      setUser(data.user);
      navigate('/notes');
    } catch (err) {
      setFormError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="login-story">
        <p className="eyebrow">Notes</p>
        <h1>A repository, or a topic, turned into something you can study.</h1>
        <p className="lede">
          Files become separate documents. Folders stay folders. A flat repository is sorted into subjects such as DSA and SQL. You read it before it is saved.
        </p>
        <article className="sample-note">
          <p className="sample-kicker">DSA · Two Sum</p>
          <h2>Keep a map of values you have already seen.</h2>
          <p>For each number, the complement is the value that would finish the pair. One pass is enough when the map is updated as you go.</p>
          <div className="sample-table">
            <span>Case</span><span>Time</span><span>Space</span>
            <span>Hash map</span><span>O(n)</span><span>O(n)</span>
            <span>Sort and scan</span><span>O(n log n)</span><span>O(1)</span>
          </div>
        </article>
      </section>
      <section className="login-panel">
        <ThemeToggle />
        <div className="login-card">
          <h2>Sign in</h2>
          <p>The first screen is always sign-in. Google is the account for your notes.</p>
          {error ? (
            <>
              <p className="form-error">{error}</p>
              <button type="button" className="button button-quiet" onClick={() => refresh().catch(() => {})}>Try again</button>
            </>
          ) : null}
          {authMessage ? <p className="form-error">{authMessage}</p> : null}
          {formError ? <p className="form-error">{formError}</p> : null}
          {config?.google ? (
            <a className="button button-primary" href="/api/auth/google">Continue with Google</a>
          ) : (
            <button type="button" className="button button-primary" disabled>
              Continue with Google
            </button>
          )}
          {config && !config.google ? (
            <p className="fine">
              Google OAuth keys are not in the server environment yet. Add <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> before anyone else uses this app.
            </p>
          ) : null}
          {config?.devLogin ? (
            <button type="button" className="button button-quiet" onClick={preview} disabled={busy}>
              {busy ? 'Opening preview…' : 'Continue with a local preview'}
            </button>
          ) : null}
        </div>
      </section>
    </div>
  );
}
