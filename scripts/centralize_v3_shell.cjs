// One-time extraction of shared GST chrome's static UI copy into its copy module.
const fs=require('fs'),path=require('path'),ts=require('../frontend/node_modules/typescript');
if(fs.readFileSync('frontend/lib/copy/gst.ts','utf8').includes('export const GST_TEXT'))throw new Error('This one-time copy migration has already been applied.');
const files=['workspace.tsx','customer-dashboard.tsx','gst-workspace.tsx','account-menu.tsx','v7-panels.tsx'];
const labels=new Map();
const decode=s=>s.replaceAll('&amp;','&').replaceAll('&gt;','>').replaceAll('&lt;','<').replaceAll('&nbsp;',' ');
function term(text){text=decode(text.trim().replace(/\s+/g,' '));if(!labels.has(text))labels.set(text,`text${labels.size+1}`);return `GST_TEXT.${labels.get(text)}`;}
for(const name of files){const file=path.join('frontend/app',name);let code=fs.readFileSync(file,'utf8');const ast=ts.createSourceFile(file,code,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),edits=[];
 function visit(n){
  if(ts.isJsxText(n)&&n.text.trim()&&/[A-Za-z]/.test(n.text))edits.push([n.getStart(ast),n.end,`{${term(n.text)}}`]);
  else if(ts.isStringLiteral(n)){
   const parent=n.parent;
   if(ts.isJsxAttribute(parent)&&['title','placeholder','aria-label','alt','text','label'].includes(parent.name.getText(ast)))edits.push([n.getStart(ast),n.end,`{${term(n.text)}}`]);
   else if(!ts.isJsxAttribute(parent)&&!ts.isImportDeclaration(parent)&&!ts.isExportDeclaration(parent)&&!ts.isExpressionStatement(parent)&&!(ts.isPropertyAssignment(parent)&&parent.name===n)&&/^[A-Z][A-Za-z ]/.test(n.text)&&/[a-z]/.test(n.text))edits.push([n.getStart(ast),n.end,term(n.text)]);
  }
  ts.forEachChild(n,visit);
 }
 visit(ast);for(const [start,end,value] of edits.sort((a,b)=>b[0]-a[0]))code=code.slice(0,start)+value+code.slice(end);
 if(edits.length){const statement="import {GST_TEXT} from '../lib/copy/gst'\n";code=code.startsWith("'use client'")?code.replace("'use client'",`'use client'\n${statement}`):statement+code;fs.writeFileSync(file,code);}
}
fs.appendFileSync('frontend/lib/copy/gst.ts','\nexport const GST_TEXT = '+JSON.stringify(Object.fromEntries([...labels].map(([text,key])=>[key,text])),null,2)+' as const\n');
