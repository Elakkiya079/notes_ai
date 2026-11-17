import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import DocumentView from '../components/DocumentView';

export default function Review() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [error, setError] = useState('');
  const [drafts, setDrafts] = useState(null);
  const [selectedId, setSelectedId] = useState('');
  const [knownFolders, setKnownFolders] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let stop = false;
    let timer;
    async function tick() {
      try {
        const data = await api(`/api/import/${jobId}`);
        if (stop) return;
        setJob(data.job);
        if (data.job.status === 'fetching' || data.job.status === 'generating') {
          timer = setTimeout(tick, 1200);
        }
      } catch (err) {
        if (!stop) setError(err.message);
      }
    }
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [jobId]);

  useEffect(() => {
    if (job?.status === 'review' && !drafts) {
      const next = job.documents.map((doc) => ({ ...doc, included: doc.included && !doc.error }));
      setDrafts(next);
      const first = next.find((doc) => doc.markdown) || next[0];
      if (first) setSelectedId(first.id);
    }
  }, [job, drafts]);

  useEffect(() => {
    api('/api/folders').then((data) => setKnownFolders(data.folders.map((folder) => folder.name))).catch(() => {});
  }, []);

  const selected = drafts?.find((doc) => doc.id === selectedId) || null;
  const includedCount = drafts?.filter((doc) => doc.included).length || 0;
  const folderNames = useMemo(() => {
    const names = new Set(knownFolders);
    drafts?.forEach((doc) => names.add(doc.folderName));
    return [...names].filter(Boolean);
  }, [drafts, knownFolders]);

  function updateDraft(id, patch) {
    setDrafts((current) => current.map((doc) => (doc.id === id ? { ...doc, ...patch } : doc)));
  }

  async function save() {
    setSaving(true);
    setError('');
    try {
      const data = await api(`/api/import/${jobId}/save`, {
        method: 'POST',
        body: {
          documents: drafts.map((doc) => ({
            id: doc.id,
            title: doc.title,
            folderName: doc.folderName,
            included: doc.included,
          })),
        },
      });
      const first = data.notes[0];
      navigate(`/notes/${first.folderSlug}/${first.id}`);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  if (error && !job) return <p className="page-error">{error}</p>;
  if (!job) return <p className="quiet page-pad">Preparing the import…</p>;

  const working = job.status === 'fetching' || job.status === 'generating';
  const skippedReasons = Object.entries(job.skipped?.byReason || {});

  return (
    <div className="review">
      <header className="page-intro compact">
        <p className="eyebrow">{job.kind === 'topic' ? 'Topic' : job.repoFullName || job.input}</p>
        <h1>{working ? 'Writing the documents' : job.status === 'failed' ? 'This import stopped' : 'Review before adding'}</h1>
        {working ? (
          <p>{job.status === 'fetching' ? 'Reading the repository…' : `Drafted ${job.progress?.done || 0} of ${job.progress?.total || 0}.`}</p>
        ) : null}
        {job.status === 'failed' ? <p className="form-error">{job.error}</p> : null}
        {skippedReasons.length ? (
          <p className="fine">Skipped {job.skipped.total}: {skippedReasons.map(([reason, count]) => `${count} ${reason}`).join(', ')}.</p>
        ) : null}
        {job.skipped?.samples?.length ? (
          <ul className="skip-list">
            {job.skipped.samples.map((item) => <li key={`${item.path}-${item.reason}`}>{item.path} — {item.reason}</li>)}
          </ul>
        ) : null}
      </header>

      {job.status === 'saved' ? (
        <div className="empty">
          <h1>These documents were added</h1>
          <Link className="button button-primary" to="/notes">Open notes</Link>
        </div>
      ) : null}

      {job.status === 'failed' ? <Link className="page-pad" to="/import">Back to import</Link> : null}

      {working ? (
        <ul className="progress-list">
          {(job.documents || []).map((doc) => (
            <li key={doc.id}>{doc.error ? `${doc.title} could not be drafted` : doc.title}</li>
          ))}
        </ul>
      ) : null}

      {drafts ? (
        <div className="review-body">
          <section className="draft-list">
            {drafts.map((doc) => (
              <article key={doc.id} className={doc.id === selectedId ? 'draft active' : 'draft'}>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={doc.included}
                    disabled={Boolean(doc.error)}
                    onChange={(event) => updateDraft(doc.id, { included: event.target.checked })}
                  />
                  <span>Include</span>
                </label>
                <div className="draft-open" onClick={() => setSelectedId(doc.id)} role="presentation">
                  <input
                    value={doc.title}
                    aria-label="Document title"
                    onChange={(event) => updateDraft(doc.id, { title: event.target.value })}
                    onFocus={() => setSelectedId(doc.id)}
                    onClick={(event) => event.stopPropagation()}
                  />
                  <input
                    value={doc.folderName}
                    aria-label="Folder"
                    list="folder-names"
                    onChange={(event) => updateDraft(doc.id, { folderName: event.target.value })}
                    onFocus={() => setSelectedId(doc.id)}
                    onClick={(event) => event.stopPropagation()}
                  />
                  <small>{doc.sourcePath}</small>
                  {doc.error ? <small className="form-error">{doc.error}</small> : null}
                </div>
              </article>
            ))}
            <datalist id="folder-names">
              {folderNames.map((name) => <option key={name} value={name} />)}
            </datalist>
          </section>
          <section className="reading">
            {selected?.markdown ? <DocumentView markdown={selected.markdown} /> : <p className="quiet">Choose a document to read it.</p>}
          </section>
        </div>
      ) : null}

      {drafts ? (
        <footer className="review-bar">
          {error ? <p className="form-error">{error}</p> : <p>{includedCount} selected</p>}
          <button type="button" className="button button-primary" onClick={save} disabled={saving || includedCount === 0}>
            {saving ? 'Adding…' : 'Add to notes'}
          </button>
        </footer>
      ) : null}
    </div>
  );
}
