'use client'

import {InputHTMLAttributes, useId, useState} from 'react'

export default function PasswordInput(props: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'>) {
 const [visible, setVisible] = useState(false)
 const generatedId = useId()
 const id = props.id || generatedId
 return <span className="password-control">
  <input {...props} id={id} type={visible ? 'text' : 'password'}/>
  <button type="button" className="password-toggle" aria-label={visible ? 'Hide password' : 'Show password'} aria-controls={id} aria-pressed={visible} onClick={() => setVisible(value => !value)}>
   <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>{visible && <path d="m3 3 18 18"/>}</svg>
  </button>
 </span>
}
