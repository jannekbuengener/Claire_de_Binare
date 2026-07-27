// Mehrzeilige script as provided in the conversation -- include exact code block from earlier message
const fs = require('fs');
const path = require('path');

const GITHUB_EVENT_PATH = process.env.GITHUB_EVENT_PATH;
const GITHUB_REPOSITORY = process.env.GITHUB_REPOSITORY;
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const DEEPL_API_KEY = process.env.DEEPL_API_KEY;
const TARGET_LANG = process.env.TARGET_LANG || 'DE';

if (!GITHUB_EVENT_PATH || !GITHUB_REPOSITORY || !GITHUB_TOKEN) {
  console.error('Fehlende Umgebungsvariablen (GITHUB_EVENT_PATH / GITHUB_REPOSITORY / GITHUB_TOKEN).');
  process.exit(1);
}

const event = JSON.parse(fs.readFileSync(GITHUB_EVENT_PATH, 'utf8'));
const [owner, repo] = GITHUB_REPOSITORY.split('/');

function isAlreadyTranslation(text) {
  if (!text) return false;
  return text.includes('[Übersetzung — DE]');
}

async function translateWithDeepL(text, target) {
  const url = 'https://api-free.deepl.com/v2/translate';
  const params = new URLSearchParams();
  params.append('auth_key', DEEPL_API_KEY);
  params.append('text', text);
  params.append('target_lang', target);
  const res = await fetch(url, { method: 'POST', body: params });
  if (!res.ok) throw new Error(`DeepL Fehler: ${res.status} ${res.statusText}`);
  const j = await res.json();
  return { text: j.translations?.[0]?.text || '', detected: j.translations?.[0]?.detected_source_language || '' };
}

async function translateWithLibre(text, target) {
  const url = 'https://libretranslate.de/translate';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ q: text, source: 'auto', target: target.toLowerCase(), format: 'text' })
  });
  const raw = await res.text();
  if (!res.ok) throw new Error(`LibreTranslate Fehler: ${res.status} ${res.statusText} - ${raw.slice(0, 200)}`);
  let j;
  try {
    j = JSON.parse(raw);
  } catch (e) {
    throw new Error(`LibreTranslate Parse Fehler (${res.status}): ${raw.slice(0, 200)}`);
  }
  return { text: j.translatedText || '', detected: j.detectedLanguage || j.detectedSourceLanguage || '' };
}

async function githubRequest(pathSuffix, method = 'GET', body = null) {
  const url = `https://api.github.com${pathSuffix}`;
  const headers = {
    Authorization: `token ${GITHUB_TOKEN}`,
    'User-Agent': 'issue-translator-action',
    Accept: 'application/vnd.github.v3+json'
  };
  const opts = { method, headers };
  if (body) {
    opts.body = JSON.stringify(body);
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`GitHub API Fehler ${res.status} ${res.statusText} - ${txt}`);
  }
  return res.json();
}

async function findExistingTranslationComment(issue_number) {
  const path = `/repos/${owner}/${repo}/issues/${issue_number}/comments`;
  const comments = await githubRequest(path, 'GET');
  for (const c of comments) {
    if (c.user && (c.user.type === 'Bot' || c.user.login === 'github-actions[bot]' || c.user.login.endsWith('[bot]')) &&
        typeof c.body === 'string' && c.body.startsWith('[Übersetzung — DE]')) {
      return c;
    }
  }
  return null;
}

async function postOrUpdateTranslation(issue_number, body) {
  const existing = await findExistingTranslationComment(issue_number);
  if (existing) {
    const path = `/repos/${owner}/${repo}/issues/comments/${existing.id}`;
    return githubRequest(path, 'PATCH', { body });
  } else {
    const path = `/repos/${owner}/${repo}/issues/${issue_number}/comments`;
    return githubRequest(path, 'POST', { body });
  }
}

async function run() {
  try {
    let issue_number = null;
    let text = null;
    let source_url = null;
    if (event.issue) {
      issue_number = event.issue.number;
      if (event.comment && event.action) {
        text = event.comment.body;
        source_url = event.comment.html_url;
      } else {
        text = event.issue.body;
        source_url = event.issue.html_url;
      }
    } else {
      console.log('Kein Issue im Event gefunden — beende.');
      return;
    }

    if (!text || text.trim().length === 0) {
      console.log('Kein Text zum Übersetzen gefunden.');
      return;
    }

    if (isAlreadyTranslation(text)) {
      console.log('Text scheint bereits eine Übersetzung zu sein — überspringe.');
      return;
    }

    let result;
    if (DEEPL_API_KEY) {
      try {
        result = await translateWithDeepL(text, TARGET_LANG);
      } catch (e) {
        console.warn('DeepL fehlgeschlagen, versuche LibreTranslate als Fallback:', e.message);
        result = await translateWithLibre(text, TARGET_LANG);
      }
    } else {
      result = await translateWithLibre(text, TARGET_LANG);
    }

    const detected = result.detected || '';
    const translated = result.text || '';
    if (!translated) {
      console.log('Keine Übersetzung erhalten — beende.');
      return;
    }

    const commentBody = `[Übersetzung — DE] (Quelle: ${detected || 'unbekannt'})\n\n---\n\n${translated}\n\n---\n_Automatisch generiert von der Issue-Übersetzungs-Action. Original: ${source_url}_`;

    await postOrUpdateTranslation(issue_number, commentBody);
    console.log('Übersetzung gepostet/aktualisiert.');
  } catch (err) {
    console.error('Fehler in der Übersetzungs-Action:', err);
    process.exit(1);
  }
}

run();
