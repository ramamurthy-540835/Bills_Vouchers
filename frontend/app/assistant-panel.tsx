'use client'
import {FormEvent,useEffect,useRef,useState} from 'react'

type Source={id:string;href:string;label:string;layer:string}
type Message={role:'user'|'assistant';content:string;sources?:Source[];followups?:string[]}
type Saved={question:string;response:{answer:string;sources?:Source[];followups?:string[]};conversation_id:string;created_at:string}
function safeSource(href:string){
 if(href.startsWith('/')&&!href.startsWith('//'))return true
 try{const u=new URL(href);return u.protocol==='https:'&&['gst.gov.in','www.gst.gov.in','tutorial.gst.gov.in','taxinformation.cbic.gov.in','cbic-gst.gov.in'].includes(u.hostname)}catch{return false}
}
export default function AssistantPanel({period,scenario}:{period:string;scenario?:string}){
 return <AssistantConversation key={`${period}:${scenario||'live'}`} period={period} scenario={scenario}/>
}
function AssistantConversation({period,scenario}:{period:string;scenario?:string}){
 const [messages,setMessages]=useState<Message[]>([]),[question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const [recent,setRecent]=useState<Saved[]>([]),[historyError,setHistoryError]=useState(''),[historyLoading,setHistoryLoading]=useState(false)
 const [historyNext,setHistoryNext]=useState<number|null>(null)
 const pending=useRef(false),lastQuestion=useRef(''),conversation=useRef(''),active=useRef(true),requestAbort=useRef<AbortController|null>(null)
 const query=new URLSearchParams({period,...(scenario?{scenario}:{})}).toString()
 async function loadRecent(signal?:AbortSignal,offset=0){
  if(scenario)return
  setHistoryLoading(true)
  try{const response=await fetch(`/api/assistant/history?${query}&offset=${offset}`,{cache:'no-store',signal:signal||AbortSignal.timeout(20000)})
   if(!response.ok)throw Error(response.status===401?'Please sign in again to load your history.':'Recently asked could not be loaded. Retry history.')
   const data=await response.json();if(active.current&&!signal?.aborted){setRecent(old=>offset?[...old,...data.items]:data.items);setHistoryNext(data.next_offset);setHistoryError('')}
  }catch(e){if(active.current&&!signal?.aborted)setHistoryError(e instanceof Error?e.message:'History unavailable.')}
  finally{if(active.current&&!signal?.aborted)setHistoryLoading(false)}
 }
 useEffect(()=>{
  // Scope changes remount this component. Do not clear input in a mount effect:
  // hydration may replay the user's first keystrokes before this effect runs.
  active.current=true;if(!conversation.current)conversation.current=crypto.randomUUID()
  const abort=new AbortController();void loadRecent(abort.signal)
  return()=>{active.current=false;abort.abort();requestAbort.current?.abort()}
 },[period,scenario])
 async function ask(text=question){
  text=text.trim();if(!text||pending.current)return
  if(!conversation.current)conversation.current=crypto.randomUUID()
  pending.current=true;lastQuestion.current=text;setBusy(true);setError('');setQuestion('')
  const previous=messages;setMessages([...previous,{role:'user',content:text}])
  const abort=new AbortController();requestAbort.current=abort;const timer=setTimeout(()=>abort.abort(),60000)
  try{
   const csrf=await fetch('/api/auth/csrf',{signal:abort.signal});if(!csrf.ok)throw Error('Please sign in again.')
   const token=(await csrf.json()).token
   const response=await fetch(`/api/${scenario?'demo':'assistant'}/chat?${query}`,{method:'POST',signal:abort.signal,headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({question:text,conversation_id:conversation.current||crypto.randomUUID(),history:scenario?previous.slice(-8).map(({role,content})=>({role,content:content.slice(0,4000)})):[]})})
   const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(response.status===401?'Your session expired. Sign in again, then retry.':response.status===429?`Question limit reached. Retry after ${response.headers.get('retry-after')||60} seconds.`:data.error?.message||(typeof data.detail==='string'?data.detail:data.detail?.message)||'The assistant is unavailable. Please retry.')
   if(!active.current)return
   if(typeof data.answer!=='string')throw Error('The assistant returned an invalid answer. Please retry.')
   setMessages([...previous,{role:'user',content:text},{role:'assistant',content:data.answer,sources:data.sources,followups:data.followups}].slice(-50) as Message[])
   if(data.degraded)setError(`AI interpretation is unavailable (${data.failure_category}). Evidence remains accessible. Reference: ${data.request_id}`)
   if(data.history_saved===false)setHistoryError('This answer could not be saved to Recently asked. Please check history before leaving.')
   else if(!scenario)void loadRecent()
  }catch(e){if(active.current){setMessages(previous);setQuestion(text);setError(e instanceof Error&&e.name==='AbortError'?'The answer timed out. Your question is preserved; please retry.':e instanceof Error?e.message:'Please retry.')}}
  finally{clearTimeout(timer);pending.current=false;if(active.current)setBusy(false)}
 }
 async function clearHistory(){
  if(pending.current||!window.confirm('Clear your saved assistant history for this business and period?'))return
  pending.current=true;setBusy(true)
  try{const csrf=await fetch('/api/auth/csrf',{signal:AbortSignal.timeout(15000)});if(!csrf.ok)throw Error('Please sign in again.')
   const token=(await csrf.json()).token
   const response=await fetch(`/api/assistant/history/clear?${query}`,{method:'POST',headers:{'x-csrf-token':token},signal:AbortSignal.timeout(20000)})
   if(!response.ok)throw Error('History could not be cleared. Please retry.')
   if(active.current){setRecent([]);setHistoryNext(null);setMessages([]);setHistoryError('');conversation.current=crypto.randomUUID()}
  }catch(e){if(active.current)setHistoryError(e instanceof Error?e.message:'History could not be cleared.')}
  finally{pending.current=false;if(active.current)setBusy(false)}
 }
 function submit(e:FormEvent){e.preventDefault();void ask()}
 return <section className="bv-card assistant-panel"><div className="section-heading"><div><h2>Ask your finance assistant</h2><p className="muted">{scenario?'Synthetic demo figures only.':'Answers use the selected customer and period.'} Read-only, with source links.</p></div><button className="button quiet" disabled={busy} onClick={()=>{setMessages([]);setError('');setQuestion('');lastQuestion.current='';conversation.current=crypto.randomUUID()}}>New conversation</button></div>
 {!scenario&&<details><summary>Recently asked ({recent.length})</summary><p className="muted">Private to your account, selected business and period. Saved answers are historical; ask again for current figures. Retained for up to 90 days.</p>{historyLoading&&<p role="status">Loading your history…</p>}{!historyLoading&&!recent.length&&!historyError&&<p>No saved questions for this period.</p>}<ul>{recent.map((item,i)=><li key={item.created_at+':'+i}><button className="button quiet" disabled={busy} onClick={()=>{conversation.current=item.conversation_id;setMessages([{role:'user',content:item.question},{role:'assistant',content:item.response.answer,sources:item.response.sources,followups:item.response.followups}]);setError('');setQuestion('')}}>{item.question}</button> <small>{item.created_at}</small></li>)}</ul>{historyNext!==null&&<button className="button secondary" disabled={busy||historyLoading} onClick={()=>void loadRecent(undefined,historyNext)}>Load more questions</button>}{recent.length>0&&<button className="button secondary" disabled={busy} onClick={()=>void clearHistory()}>Clear my history</button>}</details>}
 {historyError&&<div className="notice" role="alert">{historyError}<button className="button secondary" disabled={busy} onClick={()=>void loadRecent()}>Retry history</button></div>}
 <div className="suggestions">{['What is my cash requirement?','Why is some credit deferred?','Which invoices need review?'].map(q=><button className="button secondary" key={q} disabled={busy} onClick={()=>void ask(q)}>{q}</button>)}</div>
 <div className="chat-transcript" role="log" aria-live="polite">{messages.map((m,i)=><article className={`chat-message ${m.role}`} key={i}><strong>{m.role==='user'?'You':'Finance assistant'}</strong><p>{m.content}</p>{m.sources?.length?<div className="chat-sources"><small>Sources</small>{m.sources.filter(s=>safeSource(s.href)).map(s=><a key={s.id} href={s.href}>{s.label} <span className="chip">{s.layer}</span></a>)}</div>:null}{m.followups?.length?<div className="suggestions">{m.followups.map(q=><button className="button quiet" key={q} disabled={busy} onClick={()=>void ask(q)}>{q}</button>)}</div>:null}</article>)}{busy&&<p role="status">Checking the available figures and evidence…</p>}</div>
 {error&&<div className="notice" role="alert">{error}<button className="button secondary" disabled={busy||!lastQuestion.current} onClick={()=>void ask(lastQuestion.current)}>Retry question</button></div>}<form className="assistant-input" onSubmit={submit}><label htmlFor="assistant-question">Your question</label><textarea id="assistant-question" value={question} maxLength={1200} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about tax, credit or an invoice…" disabled={busy}/><div><small className="muted">AI answers can be mistaken. Check the linked records before acting.</small><button className="button primary" disabled={busy||!question.trim()}>{busy?'Answering…':'Ask assistant'}</button></div></form>
 </section>
}
