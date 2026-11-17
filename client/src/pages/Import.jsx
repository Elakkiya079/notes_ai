import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../context/AuthContext';

export default function ImportPage() {
  const { config, user, refresh } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [topic, setTopic] = useState('');
  const [repos, setRepos] = useState([]);
  const [repoError, setRepoError] = useState('');
  const [topicError, setTopicError] = useState('');
  const [busy, setBusy] = useState('');

  useEffect(() => {
    if (!user?.github) return undefined;
    api('/api/github/repos')
      .then((data) => setRepos(data.repos || []))
      .catch((err) => setRepoError(err.message));
  }, [user?.github]);

  const githubState = params.get('github');
  useEffect(() => {
    if (githubState === 'connected') refresh().catch(() => {});
  }, [githubState]);

  const geminiReady = Boolean(config?.gemini);
  const githubNotice = {
    connected: 'GitHub is connected. Private repositories can be read with your account.',
    denied: 'GitHub connection was cancelled.',
    error: 'GitHub could not be connected. Check the OAuth app settings.',
  }[params.get('github')];

  async function submitRepo(event, nextUrl = url) {
    event?.preventDefault();
    setBusy('repo');
    setRepoError('');
    try {
      const data = await api('/api/import/repo', { method: 'POST', body: { url: nextUrl } });
      navigate(`/import/${data.job.id}`);
    } catch (err) {
      setRepoError(err.message);
    } finally {
      setBusy('');
    }
  }

  async function submitTopic(event) {
    event.preventDefault();
    setBusy('topic');
    setTopicError('');
    try {
      const data = await api('/api/import/topic', { method: 'POST', body: { topic } });
      navigate(`/import/${data.job.id}`);
    } catch (err) {
      setTopicError(err.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="import-page">
      <header className="page-intro">
        <p className="eyebrow">Import</p>
        <h1>Bring in a repository or ask for a topic.</h1>
        <p>
          A repository with folders keeps a document for each file inside that folder. A repository that is only files is sorted by subject. A topic becomes one document in the folder that fits it. Nothing is saved until you review it.
        </p>
      </header>
      {!geminiReady ? (
        <p className="banner">Gemini is not configured. Add <code>GEMINI_API_KEY</code> to the server environment before generating documents.</p>
      ) : null}
      {githubNotice ? <p className="banner">{githubNotice}</p> : null}
      <div className="import-grid">
        <form className="panel" onSubmit={(event) => submitRepo(event)}>
          <h2>Repository</h2>
          <p>Paste a public <code>owner/repo</code> URL, or pick one of yours after connecting GitHub.</p>
          <label htmlFor="repo-url">GitHub repository</label>
          <input
            id="repo-url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://github.com/owner/repo"
            autoComplete="off"
          />
          {repoError ? <p className="form-error">{repoError}</p> : null}
          <button className="button button-primary" type="submit" disabled={!geminiReady || busy === 'repo' || !url.trim()}>
            {busy === 'repo' ? 'Reading repository…' : 'Fetch and draft'}
          </button>
          {user?.github ? (
            <div className="repo-list">
              <h3>Your repositories</h3>
              {repos.length ? repos.map((repo) => (
                <button
                  type="button"
                  key={repo.fullName}
                  className="repo-row"
                  onClick={() => {
                    setUrl(repo.fullName);
                    submitRepo(null, repo.fullName);
                  }}
                  disabled={!geminiReady || busy === 'repo'}
                >
                  <strong>{repo.fullName}</strong>
                  <span>{repo.private ? 'Private' : 'Public'}{repo.language ? ` · ${repo.language}` : ''}</span>
                </button>
              )) : <p className="quiet">No repositories were returned.</p>}
            </div>
          ) : (
            <p className="fine">Connect GitHub from the sidebar when you need a private repository. Public URLs do not need a connection.</p>
          )}
        </form>
        <form className="panel" onSubmit={submitTopic}>
          <h2>Topic</h2>
          <p>One study document, filed in the subject Gemini chooses. You can move it before saving.</p>
          <label htmlFor="topic">Topic</label>
          <input
            id="topic"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="Binary search"
            autoComplete="off"
          />
          {topicError ? <p className="form-error">{topicError}</p> : null}
          <button className="button button-primary" type="submit" disabled={!geminiReady || busy === 'topic' || topic.trim().length < 2}>
            {busy === 'topic' ? 'Writing…' : 'Create document'}
          </button>
        </form>
      </div>
    </div>
  );
}
