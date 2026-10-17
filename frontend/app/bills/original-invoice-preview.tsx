'use client'
import {useEffect,useState} from 'react'
import {FileText,Maximize2} from 'lucide-react'

export default function OriginalInvoicePreview({invoiceId,filename,source}:{invoiceId:string;filename:string;source:string}){
 const url=`/api/gst/bills/${encodeURIComponent(invoiceId)}/original`
 const spreadsheet=/\.(csv|xlsx)$/i.test(source)
 const [preview,setPreview]=useState(''),[pages,setPages]=useState<number|null>(null)
 const [loading,setLoading]=useState(!spreadsheet),[failed,setFailed]=useState(false)
 useEffect(()=>{
  const controller=new AbortController();let disposed=false,objectUrl='',task:import('pdfjs-dist').PDFDocumentLoadingTask|undefined
  setPreview('');setPages(null);setFailed(false);setLoading(!spreadsheet)
  if(!spreadsheet)(async()=>{
   try{
    const response=await fetch(url,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(30000)])})
    if(!response.ok)throw Error('Original unavailable')
    const blob=await response.blob()
    if(disposed)return
    if(blob.type==='application/pdf'){
     const pdfjs=await import('pdfjs-dist')
     if(disposed)return
     pdfjs.GlobalWorkerOptions.workerSrc='/pdfjs/pdf.worker.min.mjs'
     task=pdfjs.getDocument({data:new Uint8Array(await blob.arrayBuffer()),
      standardFontDataUrl:'/pdfjs/standard_fonts/',cMapUrl:'/pdfjs/cmaps/',cMapPacked:true,wasmUrl:'/pdfjs/wasm/'})
     const pdf=await task.promise,page=await pdf.getPage(1)
     const natural=page.getViewport({scale:1}),viewport=page.getViewport({scale:Math.min(1200/natural.width,1600/natural.height)})
     const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height)
     await page.render({canvas,viewport}).promise
     if(!disposed){setPreview(canvas.toDataURL('image/png'));setPages(pdf.numPages)}
     await task.destroy()
    }else if(['image/png','image/jpeg'].includes(blob.type)){
     objectUrl=URL.createObjectURL(blob);if(!disposed)setPreview(objectUrl)
    }else throw Error('Preview unavailable')
   }catch{if(!disposed)setFailed(true)}finally{if(!disposed)setLoading(false)}
  })()
  return()=>{disposed=true;controller.abort();if(objectUrl)URL.revokeObjectURL(objectUrl);void task?.destroy()}
 },[url,spreadsheet])
 return <aside className="bv-card original-bill"><h2>Original Invoice</h2><p className="muted">Click the invoice to view the full document.</p>
  <a className="original-invoice-preview" href={url} target="_blank" rel="noopener noreferrer" aria-label="Open full original invoice" aria-busy={loading}>
   {preview&&!failed?<img src={preview} alt={`Original invoice preview: ${filename}`} onError={()=>setFailed(true)}/>:<span className="original-preview-fallback"><FileText size={36} aria-hidden/><strong>{filename}</strong><span>{loading?'Loading preview…':spreadsheet?'Spreadsheet original — open to view or download.':'Preview unavailable. Open the original document.'}</span></span>}
   <span className="original-preview-expand" aria-hidden><Maximize2 size={16}/></span>
  </a>
  <p className="original-preview-status" role="status">{pages?`Page 1 of ${pages}${pages>1?' · Open the full document to view all pages.':''}`:loading?'Preparing document preview…':failed?'Invoice review remains available.':''}</p>
  <a className="button secondary" href={url} target="_blank" rel="noopener noreferrer">View Original Bill</a>
 </aside>
}
