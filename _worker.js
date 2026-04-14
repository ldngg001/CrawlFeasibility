import { onRequestPost } from './functions/scan.js';

export default {
  async fetch(request, env, ctx) {
    if (request.method === 'POST' && request.url.endsWith('/scan')) {
      return await onRequestPost({ request, env, ctx });
    }
    return new Response('Not Found', { status: 404 });
  }
};