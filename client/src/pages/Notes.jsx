import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import DocumentView from '../components/DocumentView';

export default function Notes() {
  const { folderSlug, noteId } = useParams();
  const navigate = useNavigate();
  const [folders, setFolders] = useState(null);
  const [error, setError] = useState('');
  const [note, setNote] = useState(null);
  const [folderName, setFolderName] = useState('');
  const [renaming, setRenaming] = useState(false);

  async function loadFolders() {
    const data = await api('/api/folders');
    setFolders(data.folders);
    return data.folders;
  }

  useEffect(() => {
    loadFolders().catch((err) => setError(err.message));
  }, []);

  const folder = folders?.find((item) => item.slug === folderSlug) || null;

  useEffect(() => {
    if (folders && !folderSlug && folders[0]) {
      navigate(`/notes/${folders[0].slug}`, { replace: true });
    }
  }, [folders, folderSlug, navigate]);

  useEffect(() => {
    setFolderName(folder?.name || '');
  }, [folder?.id, folder?.name]);

  useEffect(() => {
    if (!noteId) {
      setNote(null);
      return undefined;
    }
    let cancelled = false;
    setNote(undefined);
    api(`/api/notes/${noteId}`)
      .then((data) => {
        if (!cancelled) setNote(data.note);
      })
      .catch((err) => {
        if (!cancelled) {
          setNote(null);
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [noteId]);

  async function renameFolder(event) {
    event.preventDefault();
    if (!folder) return;
    setRenaming(true);
    setError('');
    try {
      const data = await api(`/api/folders/${folder.id}`, { method: 'PATCH', body: { name: folderName } });
      await loadFolders();
      navigate(noteId ? `/notes/${data.folder.slug}/${noteId}` : `/notes/${data.folder.slug}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setRenaming(false);
    }
  }

  async function removeFolder() {
    if (!folder || !window.confirm(`Delete ${folder.name} and every document inside it?`)) return;
    await api(`/api/folders/${folder.id}`, { method: 'DELETE' });
    await loadFolders();
    navigate('/notes');
  }

  async function removeNote() {
    if (!note || !window.confirm(`Delete ${note.title}?`)) return;
    await api(`/api/notes/${note.id}`, { method: 'DELETE' });
    await loadFolders();
    navigate(`/notes/${folderSlug}`);
  }

  if (error && !folders) return <p className="page-error">{error}</p>;
  if (!folders) return <p className="quiet page-pad">Loading notes…</p>;

  return (
    <div className="notes">
      <header className="folder-bar">
        {folders.length ? folders.map((item) => (
          <Link key={item.id} to={`/notes/${item.slug}`} className={item.slug === folderSlug ? 'folder-chip active' : 'folder-chip'}>
            {item.name}
            <span>{item.notes.length}</span>
          </Link>
        )) : <p className="quiet">Folders appear here after you add a document.</p>}
      </header>
      {error ? <p className="form-error page-pad">{error}</p> : null}
      {!folders.length ? (
        <div className="empty">
          <h1>Nothing filed yet</h1>
          <p>Import a repository or a topic. Review the documents, then add the ones you want to keep.</p>
          <Link className="button button-primary" to="/import">Import something</Link>
        </div>
      ) : folder ? (
        <div className="notes-body">
          <section className="topic-list">
            <form className="rename" onSubmit={renameFolder}>
              <label htmlFor="folder-name">Folder</label>
              <input id="folder-name" value={folderName} onChange={(event) => setFolderName(event.target.value)} />
              <button type="submit" disabled={renaming || folderName.trim() === folder.name}>Rename</button>
            </form>
            {folder.notes.length ? folder.notes.map((item) => (
              <Link key={item.id} to={`/notes/${folder.slug}/${item.id}`} className={item.id === noteId ? 'topic active' : 'topic'}>
                {item.title}
              </Link>
            )) : <p className="quiet">This folder has no documents.</p>}
            <button type="button" className="text-danger" onClick={removeFolder}>Delete folder</button>
          </section>
          <section className="reading">
            {!noteId ? <div className="empty inline"><h1>{folder.name}</h1><p>Choose a topic to read the document.</p></div> : null}
            {noteId && note === undefined ? <p className="quiet">Opening document…</p> : null}
            {note ? (
              <>
                <header className="doc-head">
                  <p className="eyebrow">{note.folderName}</p>
                  <div className="doc-title-row">
                    <h1>{note.title}</h1>
                    <button type="button" className="text-danger" onClick={removeNote}>Delete</button>
                  </div>
                  <p className="source-line">
                    {note.source === 'topic' ? `Topic · ${note.path}` : `${note.repo || 'Repository'}${note.path ? ` · ${note.path}` : ''}`}
                  </p>
                </header>
                <DocumentView markdown={note.markdown} />
              </>
            ) : null}
          </section>
        </div>
      ) : (
        <div className="empty">
          <h1>That folder is not here</h1>
          <Link to="/notes">Back to notes</Link>
        </div>
      )}
    </div>
  );
}
