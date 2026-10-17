import {mkdirSync,copyFileSync,cpSync} from 'node:fs'
const source=new URL('../node_modules/pdfjs-dist/',import.meta.url)
const target=new URL('../public/pdfjs/',import.meta.url)
mkdirSync(target,{recursive:true})
copyFileSync(new URL('build/pdf.worker.min.mjs',source),new URL('pdf.worker.min.mjs',target))
copyFileSync(new URL('LICENSE',source),new URL('LICENSE',target))
for(const folder of ['standard_fonts','cmaps','wasm'])cpSync(new URL(folder,source),new URL(folder,target),{recursive:true})
