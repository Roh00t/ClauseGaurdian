// frontend/auth.js — v3 Supabase auth (sign up / sign in / sign out).
// Loaded as an ES module. Config (URL + anon key) fetched from /api/config
// so the publishable key is never hardcoded in source.
//
// Guardrail #15: 2FA is never mandatory. signup does NOT require 2FA.
// Guardrail #16: Stripe not wired — tier='paid' only via manual Supabase edit.

let _supabase = null;

async function _getClient() {
  if (_supabase) return _supabase;
  // Lazy import supabase-js UMD from CDN (loaded once)
  if (!window.supabase) {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js';
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  const { data: cfg } = await fetch('/api/config').then(r => r.json()).then(d => ({ data: d })).catch(() => ({ data: null }));
  if (!cfg?.supabase_url || !cfg?.supabase_anon_key) throw new Error('Auth config unavailable');
  _supabase = window.supabase.createClient(cfg.supabase_url, cfg.supabase_anon_key);
  return _supabase;
}

export async function getSession() {
  try {
    const sb = await _getClient();
    const { data } = await sb.auth.getSession();
    return data?.session || null;
  } catch { return null; }
}

export async function getAccessToken() {
  const session = await getSession();
  return session?.access_token || null;
}

export async function getCurrentUser() {
  try {
    const sb = await _getClient();
    const { data } = await sb.auth.getUser();
    return data?.user || null;
  } catch { return null; }
}

export async function signUp(email, password) {
  const sb = await _getClient();
  // 2FA never mandatory at signup (guardrail #15)
  const { data, error } = await sb.auth.signUp({ email, password });
  if (error) throw error;
  return data;
}

export async function signIn(email, password) {
  const sb = await _getClient();
  const { data, error } = await sb.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

export async function signOut() {
  try {
    const sb = await _getClient();
    await sb.auth.signOut();
  } catch {}
}

export async function onAuthStateChange(callback) {
  try {
    const sb = await _getClient();
    sb.auth.onAuthStateChange((event, session) => callback(event, session));
  } catch {}
}
