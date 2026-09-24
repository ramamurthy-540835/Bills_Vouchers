'use client'
import {FormEvent,useRef,useState} from 'react'

type Message={role:'user'|'assistant';content:string;sources?:any[];followups?:string[]}
export default function AssistantPanel({period,scenario}:{period:string;scenario?:string}){
 const [messages,setMessages]=useState<Message[]>([]),[question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const pending=useRef(false)
 async function ask(text=question){
  text=text.trim();if(!text||pending.current)return
  pending.current=true;setBusy(true);setError('');setQuestion('')
  const previous=messages;setMessages([...previous,{role:'user',content:text}])
  try{
   const csrf=await fetch('/api/auth/csrf');if(!csrf.ok)throw Error('Please sign in again.')
   const token=(await csrf.json()).token
   const query=new URLSearchParams({period,...(scenario?{scenario}:{})})
   const response=await fetch(`/api/${scenario?'demo':'assistant'}/chat?${query}`,{method:'POST',headers:{'content-type':'application/json','x-csrf-token':token},body:JSON.stringify({question:text,history:previous.slice(-8).map(({role,content})=>({role,content:content.slice(0,4000)}))})})
   const data=await response.json();if(!response.ok)throw Error(data.error?.message||data.detail||'The assistant is unavailable. Please retry.')
   setMessages([...previous,{role:'user',content:text},{role:'assistant',content:data.answer,sources:data.sources,followups:data.followups}])
  }catch(e){setMessages(previous);setQuestion(text);setError(e instanceof Error?e.message:'Please retry.')}
  finally{pending.current=false;setBusy(false)}
 }
 function submit(e:FormEvent){e.preventDefault();ask()}
 return <section className="bv-card assistant-panel"><div className="section-heading"><div><h2>Ask your finance assistant</h2><p className="muted">{scenario?'Synthetic demo figures only.':'Answers use the selected customer and period.'} Read-only, with source links.</p></div><button className="button quiet" disabled={busy} onClick={()=>{setMessages([]);setError('')}}>New conversation</button></div>
 <div className="suggestions">{['What is my cash requirement?','Why is some credit deferred?','Which invoices need review?'].map(q=><button className="button secondary" key={q} disabled={busy} onClick={()=>ask(q)}>{q}</button>)}</div>
 <div className="chat-transcript" role="log" aria-live="polite">{messages.map((m,i)=><article className={`chat-message ${m.role}`} key={i}><strong>{m.role==='user'?'You':'Finance assistant'}</strong><p>{m.content}</p>{m.sources?.length? <div className="chat-sources"><small>Sources</small>{m.sources.map(s=><a key={s.id} href={s.href}>{s.label} <span className="chip">{s.layer}</span></a>)}</div>:null}{m.followups?.length?<div className="suggestions">{m.followups.map(q=><button className="button quiet" key={q} disabled={busy} onClick={()=>ask(q)}>{q}</button>)}</div>:null}</article>)}{busy&&<p role="status">Checking the available figures and evidence…</p>}</div>
 {error&&<p className="notice" role="alert">{error}</p>}<form className="assistant-input" onSubmit={submit}><label htmlFor="assistant-question">Your question</label><textarea id="assistant-question" value={question} maxLength={1200} onChange={e=>setQuestion(e.target.value)} placeholder="Ask about tax, credit or an invoice…" disabled={busy}/><div><small className="muted">AI answers can be mistaken. Check the linked records before acting.</small><button className="button primary" disabled={busy||!question.trim()}>{busy?'Answering…':'Ask assistant'}</button></div></form>
 </section>
}
