(() => {
  const briefing = document.querySelector('.briefing');
  if (briefing) {
    const section = document.createElement('section');
    section.className = 'briefing section-shell';
    section.setAttribute('aria-labelledby', 'plain-language-title');
    section.innerHTML = `
      <div class="section-heading split-heading"><div><p class="section-label">ETS IN PLAIN ENGLISH</p><h2 id="plain-language-title">A simple conversation about ETS</h2></div><p>A straightforward introduction to what Evidence Transparency Systems are, how ETS works, and why verifiable evidence matters—without the technical deep dive.</p></div>
      <div class="audio-shell"><div id="elevenlabs-audionative-widget" data-height="90" data-width="100%" data-frameborder="no" data-scrolling="no" data-publicuserid="9e8765876d220a246c6623290d83285470427384185db18970c9cfae44d68fe3" data-playerurl="https://elevenlabs.io/player/index.html" data-projectid="cb5tvaKJ7SgYQ6967yyK" >Loading the <a href="https://elevenlabs.io/text-to-speech" target="_blank" rel="noopener">Elevenlabs Text to Speech</a> AudioNative Player...</div></div>`;
    briefing.insertAdjacentElement('afterend', section);
    const playerScript = document.createElement('script'); playerScript.src = 'https://elevenlabs.io/player/audioNativeHelper.js'; playerScript.type = 'text/javascript'; document.body.appendChild(playerScript);
  }

  const signal = document.querySelector('.signal-strip');
  if (signal) {
    const showcase = document.createElement('section');
    showcase.className = 'launch-showcase section-shell';
    showcase.id = 'latest';
    showcase.innerHTML = `
      <div class="launch-heading"><div><p class="section-label">NOW BUILDING ON ETS</p><h2>Enterprise evidence meets mobile provenance.</h2><p>Lantern Protocol now extends the ETS evidence fabric into Microsoft 365 and onto iOS and Android. M365 Connector is entering beta. Provenance mobile applications are in active development.</p></div><a class="button button-primary" href="#early-access">Get early access updates ↗</a></div>
      <div class="launch-feature-grid">
        <article class="m365-card"><div><span class="release-badge">BETA</span><h3>M365 Connector</h3><p>Bring evidence-native verification into Microsoft 365 while preserving independently verifiable provenance beyond the application that created the evidence.</p><ul><li>SharePoint integration first</li><li>Preserve, hash, attest and verify</li><li>Maintain evidence lineage across M365 workflows</li></ul></div><div class="m365-mark" aria-label="Microsoft 365"><span class="ms-window"><i></i><i></i><i></i><i></i></span><strong>Microsoft 365</strong></div></article>
        <article class="provenance-card"><div><span class="release-badge dev">IN DEVELOPMENT</span><h3>Provenance</h3><p>Capture. Protect. Prove. Anywhere. Provenance extends ETS to the point where mobile evidence originates.</p><div class="platform-badges"><span>iOS development</span><span>Android development</span></div><small>Dev/Lite and Professional editions are planned.</small></div><div class="phone-pair" aria-hidden="true"><div class="phone"><b>Provenance</b><span>✓</span><small>Evidence captured</small></div><div class="phone second"><b>Provenance</b><span>✓</span><small>Proof ready</small></div></div></article>
      </div>
      <div class="fabric-panel"><div class="fabric-title"><p class="section-label">THE COMPLETE ETS PLATFORM</p><h3>One evidence fabric. From capture to independent proof.</h3></div><div class="fabric-grid">
        <div><b>EDGE</b><span>Capture & secure</span></div><div><b>GATEWAY</b><span>Ingest & route</span></div><div><b>ETS VERIFY</b><span>Independent proof</span></div><div><b>AI WITNESS</b><span>Attest & anchor</span></div><div><b>VAULT</b><span>Retain & govern</span></div><div><b>BLACK BOX</b><span>High-assurance capture</span></div><div><b>COMPLIANCE</b><span>Policy & audit</span></div><div><b>EXCHANGE</b><span>Portable evidence</span></div>
      </div><div class="protocol-rail"><strong>ETS PROTOCOL</strong><span>Vendor-neutral evidence objects • provenance • cryptographic binding • portable verification</span></div></div>
      <form class="early-access" id="early-access"><div><p class="section-label">EARLY ACCESS</p><h3>Be first in line.</h3><p>M365 Connector is in beta and Provenance is in development. Tell us what you want to test.</p></div><div class="early-fields"><input type="email" name="email" placeholder="Work email address" aria-label="Work email address" required><input type="text" name="organization" placeholder="Organization (optional)" aria-label="Organization"><div class="interest-grid"><label><input type="checkbox" name="release" value="M365 Connector Beta"> M365 Connector Beta</label><label><input type="checkbox" name="release" value="Provenance iOS"> Provenance iOS</label><label><input type="checkbox" name="release" value="Provenance Android"> Provenance Android</label><label><input type="checkbox" name="release" value="All developer releases"> All developer releases</label></div><button class="button button-primary" type="submit">Notify me ↗</button><p class="early-status" aria-live="polite"></p></div></form>
    `;
    signal.insertAdjacentElement('afterend', showcase);

    const style = document.createElement('style');
    style.textContent = `.launch-showcase{background:radial-gradient(circle at 70% 12%,rgba(35,91,185,.2),transparent 28%),#080b12}.launch-heading{display:grid;grid-template-columns:1fr auto;gap:40px;align-items:end;margin-bottom:34px}.launch-heading>div{max-width:880px}.launch-heading h2{margin-bottom:16px}.launch-feature-grid{display:grid;grid-template-columns:1.15fr .85fr;gap:16px}.launch-feature-grid article{min-height:360px;border:1px solid #31465d;padding:30px;background:linear-gradient(145deg,rgba(22,31,61,.92),rgba(8,13,25,.96));display:grid;grid-template-columns:1fr auto;gap:25px;overflow:hidden}.provenance-card{border-color:#1b675f!important;background:linear-gradient(145deg,rgba(7,43,45,.72),rgba(8,13,25,.96))!important}.release-badge{display:inline-block;border:1px solid #697cff;color:#aab5ff;padding:4px 8px;font-size:.62rem;letter-spacing:.12em;border-radius:20px;margin-bottom:15px}.release-badge.dev{border-color:#27b7a8;color:#75ddd2}.launch-feature-grid h3{font-size:1.8rem;margin-bottom:10px}.launch-feature-grid ul{padding-left:18px;color:#c5cad1}.m365-mark{align-self:center;display:grid;place-items:center;gap:14px;min-width:210px;font-size:1.5rem}.ms-window{width:82px;height:82px;display:grid;grid-template-columns:1fr 1fr;gap:5px}.ms-window i:nth-child(1){background:#f35325}.ms-window i:nth-child(2){background:#81bc06}.ms-window i:nth-child(3){background:#05a6f0}.ms-window i:nth-child(4){background:#ffba08}.platform-badges{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}.platform-badges span{border:1px solid #416d70;padding:7px 10px;font-size:.68rem;text-transform:uppercase}.phone-pair{display:flex;align-items:center;min-width:220px}.phone{width:120px;height:245px;border:4px solid #56616b;border-radius:22px;background:#07111e;padding:20px 10px;display:grid;place-items:center;text-align:center;box-shadow:0 15px 40px #0008}.phone span{font-size:3rem;color:#72d7ae}.phone small{color:#8fa2ad}.phone.second{margin-left:-28px;transform:translateY(15px)}.fabric-panel{margin-top:16px;border:1px solid #283b50;padding:28px;background:#090e18}.fabric-title{text-align:center}.fabric-title h3{font-size:1.5rem}.fabric-grid{display:grid;grid-template-columns:repeat(8,1fr);margin-top:25px}.fabric-grid div{padding:18px 10px;text-align:center;border-right:1px solid #26394c}.fabric-grid div:last-child{border:0}.fabric-grid b{display:block;font-size:.74rem;color:#f4f5f7}.fabric-grid span{display:block;color:#7f8d9d;font-size:.67rem;margin-top:7px}.protocol-rail{margin-top:18px;border:1px solid #245b8d;padding:10px 16px;display:flex;justify-content:center;gap:22px;flex-wrap:wrap;color:#8dbce7}.protocol-rail strong{letter-spacing:.13em}.protocol-rail span{color:#8f9ba7}.early-access{margin-top:16px;border:1px solid #31506b;padding:28px;display:grid;grid-template-columns:.65fr 1.35fr;gap:35px;background:linear-gradient(90deg,#0c1726,#090d16)}.early-fields{display:grid;grid-template-columns:1fr 1fr;gap:12px}.early-fields input[type=email],.early-fields input[type=text]{background:#09101c;border:1px solid #354a64;color:#fff;padding:13px}.interest-grid{grid-column:1/-1;display:flex;gap:18px;flex-wrap:wrap;font-size:.72rem;color:#c5ccd5}.early-fields button{width:max-content}.early-status{align-self:center;margin:0}.early-status.success{color:#91d2ab}@media(max-width:1050px){.launch-heading,.launch-feature-grid,.early-access{grid-template-columns:1fr}.fabric-grid{grid-template-columns:repeat(4,1fr);gap:1px}.m365-mark,.phone-pair{justify-self:center}}@media(max-width:720px){.launch-feature-grid article{grid-template-columns:1fr}.fabric-grid{grid-template-columns:repeat(2,1fr)}.early-fields{grid-template-columns:1fr}.early-fields>*{grid-column:1!important}.phone-pair{min-width:0}.m365-mark{min-width:0}}`;
    document.head.appendChild(style);

    const earlyForm = document.getElementById('early-access');
    earlyForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!earlyForm.reportValidity()) return;
      const data = new FormData(earlyForm);
      const releases = data.getAll('release');
      const body = `Early access request\n\nWork email: ${data.get('email')}\nOrganization: ${data.get('organization') || '(not provided)'}\nInterested in: ${releases.length ? releases.join(', ') : 'General Lantern developer releases'}\n\nSubmitted from lanternprotocol.net.`;
      const uri = `mailto:shannon.bray@echomedia.ai,shannonbraync@outlook.com?subject=${encodeURIComponent('Lantern Protocol early access request')}&body=${encodeURIComponent(body)}`;
      const status = earlyForm.querySelector('.early-status'); status.className = 'early-status success'; status.textContent = 'Your email client is opening. Send the prepared request to join the early-access list.'; window.location.href = uri;
    });
  }

  const form = document.getElementById('pilot-inquiry');
  if (!form) return;
  const status = form.querySelector('.form-status');
  const recipients = 'shannon.bray@echomedia.ai,shannonbraync@outlook.com';
  form.addEventListener('submit', (event) => {
    event.preventDefault(); if (!form.reportValidity()) return; const data = new FormData(form); if (String(data.get('website') || '').trim()) return;
    const fields = [['Name',data.get('name')],['Work email',data.get('email')],['Organization',data.get('organization')],['Role',data.get('role')],['Engagement',data.get('interest')],['Environment',data.get('environment')],['Timeline',data.get('timeline')],['Evidence path / decision',data.get('notes')]];
    const body = fields.map(([k,v]) => `${k}: ${String(v || '').trim() || '(not provided)'}`).join('\n') + '\n\nConsent: Yes — submitted from the Lantern Protocol Azure continuity site.';
    const subject = `Lantern Protocol inquiry — ${String(data.get('organization') || data.get('name') || 'website').trim()}`;
    status.className = 'form-status success'; status.textContent = 'Your email client is opening with both Lantern Protocol contact addresses included. Please send the message to complete the inquiry.'; window.location.href = `mailto:${recipients}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });
})();
