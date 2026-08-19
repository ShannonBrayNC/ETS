(() => {
  const form = document.getElementById('pilot-inquiry');
  if (!form) return;
  const status = form.querySelector('.form-status');
  const recipients = 'shannon.bray@echomedia.ai,shannonbraync@outlook.com';
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    if (String(data.get('website') || '').trim()) return;
    const fields = [
      ['Name', data.get('name')], ['Work email', data.get('email')], ['Organization', data.get('organization')],
      ['Role', data.get('role')], ['Engagement', data.get('interest')], ['Environment', data.get('environment')],
      ['Timeline', data.get('timeline')], ['Evidence path / decision', data.get('notes')]
    ];
    const body = fields.map(([k,v]) => `${k}: ${String(v || '').trim() || '(not provided)'}`).join('\n') +
      '\n\nConsent: Yes — submitted from the Lantern Protocol Azure continuity site.';
    const subject = `Lantern Protocol inquiry — ${String(data.get('organization') || data.get('name') || 'website').trim()}`;
    const uri = `mailto:${recipients}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    status.className = 'form-status success';
    status.textContent = 'Your email client is opening with both Lantern Protocol contact addresses included. Please send the message to complete the inquiry.';
    window.location.href = uri;
  });
})();
