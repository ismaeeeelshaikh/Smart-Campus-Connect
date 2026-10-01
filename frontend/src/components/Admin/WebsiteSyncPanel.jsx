import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, X, ExternalLink } from 'lucide-react';
import { adminAPI } from '../../services/api';

const formatTime = (value) => (value ? new Date(value).toLocaleString() : '—');

// Admin-only: re-read apsit.edu.in now, and see what changed
const WebsiteSyncPanel = () => {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const [pageUrl, setPageUrl] = useState('');
  const [pageBusy, setPageBusy] = useState(false);
  const [pageResult, setPageResult] = useState('');

  const load = useCallback(async () => {
    try {
      const response = await adminAPI.websiteSyncStatus();
      setStatus(response.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not load the sync status');
    }
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  // While a sync is running, refresh the progress every 3 seconds
  useEffect(() => {
    if (!open || !status?.running) return undefined;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [open, status?.running, load]);

  const startSync = async () => {
    setError('');
    try {
      await adminAPI.startWebsiteSync();
      setTimeout(load, 1000);
      setStatus((s) => ({ ...(s || {}), running: true }));
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not start the sync');
    }
  };

  const RESULT_TEXT = {
    added: 'Added to the chatbot.',
    updated: 'Changes found and updated.',
    unchanged: 'No changes since the last sync.',
    removed: 'Page no longer exists, so it was removed.',
    'no content': 'Page has no text any more, so it was removed.',
  };

  const syncOnePage = async (e) => {
    e.preventDefault();
    if (!pageUrl.trim()) return;
    setPageBusy(true);
    setPageResult('');
    setError('');
    try {
      const response = await adminAPI.syncOnePage(pageUrl.trim());
      const { status: result, title } = response.data;
      setPageResult(`${title ? `"${title}": ` : ''}${RESULT_TEXT[result] || result}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update that page');
    } finally {
      setPageBusy(false);
    }
  };

  const running = status?.running;
  const current = status?.current;
  const last = status?.last;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center space-x-2 px-3 py-1 text-accent hover:text-white rounded-md hover:bg-primary-600 transition-colors"
        title="Sync the chatbot with apsit.edu.in"
      >
        <RefreshCw className={`h-4 w-4 ${running ? 'animate-spin' : ''}`} />
        <span className="text-sm">Website sync</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-96 max-w-[90vw] bg-background-card border border-gray-700 rounded-lg shadow-xl z-50 p-4 text-sm text-gray-300">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-accent">Website sync (apsit.edu.in)</h3>
            <button onClick={() => setOpen(false)} className="text-gray-500 hover:text-white" title="Close">
              <X className="h-4 w-4" />
            </button>
          </div>

          {running ? (
            <div className="mb-3 p-2 rounded bg-background-dark border border-primary-600">
              <div className="flex items-center gap-2 text-accent">
                <RefreshCw className="h-4 w-4 animate-spin" /> Syncing…
              </div>
              {current && (
                <div className="mt-1 text-xs text-gray-400">
                  {current.pages_seen} pages checked · {current.pages_added + current.pages_updated} new or changed so far
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={startSync}
              className="w-full mb-3 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-md transition"
            >
              Sync now
            </button>
          )}

          <form onSubmit={syncOnePage} className="mb-3">
            <label className="block text-xs text-gray-500 mb-1">Just edited a page? Update only that page (takes seconds):</label>
            <div className="flex gap-2">
              <input
                type="url"
                value={pageUrl}
                onChange={(e) => setPageUrl(e.target.value)}
                placeholder="https://www.apsit.edu.in/civil-faculty"
                className="flex-1 min-w-0 px-2 py-1 rounded bg-background-dark border border-gray-700 text-gray-200 text-xs focus:outline-none focus:ring-1 focus:ring-primary-600"
              />
              <button
                type="submit"
                disabled={pageBusy || !pageUrl.trim()}
                className="px-3 py-1 text-xs bg-primary-500 hover:bg-primary-600 text-white rounded disabled:opacity-50"
              >
                {pageBusy ? 'Updating…' : 'Update'}
              </button>
            </div>
            {pageResult && <div className="mt-1 text-xs text-green-400">{pageResult}</div>}
          </form>

          {last ? (
            <div className="mb-3 text-xs space-y-1">
              <div>
                <span className="text-gray-500">Last sync:</span> {formatTime(last.finished_at)}{' '}
                <span className={last.status === 'success' ? 'text-green-400' : 'text-red-400'}>({last.status})</span>
              </div>
              <div className="text-gray-400">
                {last.pages_seen} checked · {last.pages_added} new · {last.pages_updated} changed · {last.pages_removed} removed
                {last.pages_failed > 0 && ` · ${last.pages_failed} failed`}
              </div>
              {last.error && <div className="text-yellow-400">{last.error}</div>}
            </div>
          ) : (
            !running && <div className="mb-3 text-xs text-gray-400">No sync has finished yet.</div>
          )}

          {status && (
            <div className="text-xs text-gray-500 mb-2">Pages in the chatbot's knowledge: {status.pages_indexed}</div>
          )}

          {status?.recently_changed?.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Recently changed pages</div>
              <ul className="max-h-48 overflow-y-auto space-y-1">
                {status.recently_changed.map((p) => (
                  <li key={p.url} className="text-xs flex items-start justify-between gap-2">
                    <a href={p.url} target="_blank" rel="noopener noreferrer"
                       className="text-primary-500 hover:underline truncate flex items-center gap-1">
                      {p.status === 'removed' && <span className="text-red-400">[removed]</span>}
                      <span className="truncate">{p.title}</span>
                      <ExternalLink className="h-3 w-3 flex-shrink-0" />
                    </a>
                    <span className="text-gray-500 flex-shrink-0">{formatTime(p.last_changed)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && <div className="mt-2 text-xs text-red-400">{error}</div>}
        </div>
      )}
    </div>
  );
};

export default WebsiteSyncPanel;
