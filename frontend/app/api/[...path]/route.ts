import { NextRequest, NextResponse } from 'next/server'

const backend = () => process.env.BACKEND_URL || 'http://localhost:8000'
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params
  const url = `${backend()}/api/${path.join('/')}${request.nextUrl.search}`
  const headers = new Headers(request.headers)
  headers.delete('host')
  headers.delete('content-length')
  const body = request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer()
  let response: Response
  try { response = await fetch(url, { method: request.method, headers, body, redirect: 'manual' }) }
  catch { return NextResponse.json({ detail: 'Finance backend is unavailable.' }, { status: 503 }) }
  const out = new NextResponse(response.body, { status: response.status, headers: response.headers })
  const cookie = response.headers.get('set-cookie')
  if (cookie) out.headers.set('set-cookie', cookie)
  return out
}
export const GET = proxy
export const POST = proxy
export const PUT = proxy
export const PATCH = proxy
export const DELETE = proxy
