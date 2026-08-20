(() => {
  const briefing = document.querySelector('.briefing');
  if (briefing) {
    const section = document.createElement('section');
    section.className = 'briefing section-shell';
    section.setAttribute('aria-labelledby', 'plain-language-title');
    section.innerHTML = `
      <div class="section-heading split-heading">
        <div>
          <p class="section-label">ETS IN PLAIN ENGLISH</p>
          <h2 id="plain-language-title">A simple conversation about ETS</h2>
        </div>
        <p>A straightforward introduction to what Evidence Transparency Systems are, how ETS works, and why verifiable evidence matters—without the technical deep dive.</p>
      </div>
      <div class="audio-shell">
        <div id="elevenlabs-audionative-widget" data-height="90" data-width="100%" data-frameborder="no" data-scrolling="no" data-publicuserid="9e8765876d220a246c6623290d83285470427384185db18970c9cfae44d68fe3" data-playerurl="https://elevenlabs.io/player/index.html" >Loading the <a href="https://elevenlabs.io/text-to-speech" target="_blank" rel="noopener">Elevenlabs Text to Speech</a> AudioNative Player...</div>
      </div>`;
    briefing.insertAdjacentElement('afterend', section);

    const playerScript = document.createElement('script');
    playerScript.src = 'https://elevenlabs.io/player/audioNativeHelper.js';
    playerScript.type = 'text/javascript';
    document.body.appendChild(playerScript);
  }

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
