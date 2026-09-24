"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

// Review is intentionally handled as a flyout in the document queue.  Keep
// old bookmarked /documents/:id links from opening a competing full page.
export default function LegacyDocumentRoute() {
  const router = useRouter()
  useEffect(() => { router.replace("/") }, [router])
  return <div className="loading">Opening the document workspace…</div>
}
