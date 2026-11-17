# Notes

A reading app for study notes. Sign in with Google, import a GitHub repository or a topic, let Gemini turn each file into a document, then file the ones you keep.

The API is Python (FastAPI). The interface is React. Notes are stored in MongoDB.

## Run it locally

1. Copy `.env.example` to `.env` and fill in the keys you have.
2. Start MongoDB so `MONGODB_URI` can connect.
3. Install and start both processes:

```bash
npm run install:all
npm run dev
```

The interface is at http://localhost:5173. The API is at http://localhost:5050. Port 5000 is left free because macOS AirPlay answers there and blocks Google’s sign-in callback.

Until Google OAuth is configured, the login page offers a local preview account. That account is only created when `GOOGLE_CLIENT_ID` is empty and `ENV` is not `production`.

## What an import does

- A repository with folders becomes one document per file. The note folder comes from the first meaningful directory. Names such as `src`, `lib`, and `docs` are skipped.
- A repository that is only files still becomes one document per file. Gemini chooses the folder, so DSA files and SQL files land in different folders.
- A topic becomes one document in the folder Gemini chooses.
- You can rename a document, move it, or leave it out. **Add to notes** is what saves it. Later imports merge into a folder you already have when the name matches.

Imports keep at most 25 text files and skip lockfiles, dependencies, build output, and files larger than 80 KB. The review screen lists what was skipped.

Diagrams are Mermaid, tables are markdown, and images that already live in the repository stay in the document. The app uses Gemini `gemini-3.5-flash-lite` by default. Set `GEMINI_MODEL` if you want a different model.

## Keys

Google Cloud OAuth client, with this authorized redirect URI:

`http://localhost:5050/api/auth/google/callback`

GitHub OAuth app, only needed for private repositories. Callback:

`http://localhost:5050/api/auth/github/callback`

The GitHub app needs the `repo` scope. The token is encrypted before it is stored. Public repository URLs work without connecting GitHub. `GITHUB_TOKEN` is optional and only raises the rate limit for public reads.

`GEMINI_API_KEY` comes from Google AI Studio.
