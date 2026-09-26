const fs=require('fs'),path=require('path'),ts=require('../frontend/node_modules/typescript');
const root=path.resolve('frontend');
const names={
 'GST Workspace':'GST.name','GST Filing & ITC':'GST.returns','Documents':'GST.bills',
 'Actual customer records':'GST.uploaded','Download working papers':'GST.workingPapers',
 'Eligible ITC':'GST.credit','Output tax':'GST.liability','Estimated cash':'GST.cash',
 'Non-GST purchases':'GST.nonGst','Compare estimated cash':'GST.compare','As recorded':'GST.recorded',
 'Matched to GSTR-2B':'GST.matched','After credit checks':'GST.eligible','If credit is unavailable':'GST.noCredit',
 'Including ECO cash-only liability':'GST.liabilityDetail','After tax-head set-off':'GST.cashDetail',
 'Available after credit adjustments':'GST.creditDetail','GSTIN pending':'GST.pendingGstin',
 'Your GST profile is being completed':'GST.addGstin',
};
function walk(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){
 const file=path.join(dir,entry.name);if(entry.isDirectory()){walk(file);continue}if(!file.endsWith('.tsx'))continue;
 let source=fs.readFileSync(file,'utf8');const ast=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),edits=[];
 function visit(node){
  if(ts.isStringLiteral(node)&&names[node.text]){const expression=names[node.text];edits.push([node.getStart(ast),node.end,ts.isJsxAttribute(node.parent)?`{${expression}}`:expression]);}
  if(ts.isJsxText(node)&&names[node.text.trim()])edits.push([node.getStart(ast),node.end,`{${names[node.text.trim()]}}`]);
  ts.forEachChild(node,visit);
 }
 visit(ast);if(!edits.length)continue;
 for(const [start,end,replacement] of edits.sort((a,b)=>b[0]-a[0]))source=source.slice(0,start)+replacement+source.slice(end);
 if(!/import\s*\{GST\}/.test(source)){let relative=path.relative(path.dirname(file),path.join(root,'lib/copy/gst')).replaceAll('\\','/');if(!relative.startsWith('.'))relative='./'+relative;
 const imported=`import {GST} from '${relative}'\n`;source=source.startsWith("'use client'")?source.replace("'use client'",`'use client'\n${imported}`):imported+source;}
 fs.writeFileSync(file,source);
}}
walk(path.join(root,'app'));
