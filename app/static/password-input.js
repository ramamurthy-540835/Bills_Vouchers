// Shared enhancement for the retained server-rendered account forms.
document.querySelectorAll('input[type="password"]').forEach((input, index) => {
  const id = input.id || `password-field-${index}`;
  input.id = id;
  const label = input.previousElementSibling;
  if (label && label.tagName === 'LABEL') label.htmlFor = id;
  if (!input.autocomplete) input.autocomplete = input.name === 'password' ? 'current-password' : 'new-password';
  const wrapper = document.createElement('span');
  wrapper.className = 'legacy-password-control';
  input.parentNode.insertBefore(wrapper, input);
  wrapper.appendChild(input);
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'legacy-password-toggle';
  button.setAttribute('aria-controls', id);
  button.setAttribute('aria-label', 'Show password');
  button.setAttribute('aria-pressed', 'false');
  button.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
  button.addEventListener('click', () => {
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    button.setAttribute('aria-pressed', String(visible));
  });
  wrapper.appendChild(button);
});
