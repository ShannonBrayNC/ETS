const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs/promises');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless:true,
    executablePath:process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined});
  try {
    const page = await browser.newPage({viewport:{width:1100,height:850}});
    const errors=[];
    page.on('pageerror', error=>errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../../../ets/desktop/developer.html')).href);
    for(const id of ['create-sample','bundle','trust','sample-trust','verify','sdk-export']){
      assert(await page.locator('#'+id).isDisabled(),id+' must wait for the native bridge');
    }
    assert.equal(await page.title(),'ETS Desktop Developer');
    await page.evaluate(()=>{
      window.calls={create:0,trust:0,verify:[],reports:[],sdk:0};
      window.nextCreate='success'; window.nextBundle='success'; window.nextSdk='success';
      window.hasTrust=false; window.nextStatus=null;
      window.pywebview={api:{
        create_sample:async()=>{
          window.calls.create++;
          if(window.nextCreate==='cancel')return {cancelled:true};
          if(window.nextCreate==='error')return {error:'Choose a writable parent folder.'};
          if(window.nextCreate==='reject')throw new Error('private creation detail');
          if(window.nextCreate==='hold')await new Promise(resolve=>{window.finishCreation=resolve;});
          window.hasTrust=false;
          return {created:'sample <img src=x onerror=alert(1)>',bundle:'bundle.json',
            expected_log_id:'ets-desktop-synthetic',sample_trust:false};
        },
        use_sample_trust:async()=>{window.calls.trust++;window.hasTrust=true;
          return {name:'sample-trust.json',selected:true};},
        select_bundle:async()=>{
          if(window.nextBundle==='cancel')return {cancelled:true};
          if(window.nextBundle==='error')return {error:'Unable to select this file.'};
          window.hasTrust=false;
          return {name:'<img src=x onerror=alert(1)>.json',selected:true,trust_cleared:true};
        },
        select_trust:async()=>{window.hasTrust=true;return {name:'independent-trust.json',selected:true};},
        verify:async(log)=>{
          window.calls.verify.push(log);
          const status=window.nextStatus||(window.hasTrust?'valid':'indeterminate');
          return {outcome:{status,valid:status==='valid',reason:'<script>window.injected=true</script>',
            standing_status:'checkpoint_only',checks:[{passed:status==='valid',reason:'Selected checkpoint key'}]}};
        },
        export_report:async(format)=>{window.calls.reports.push(format);return {saved:'report.'+format};},
        export_sdk:async()=>{
          window.calls.sdk++;
          if(window.nextSdk==='cancel')return {cancelled:true};
          if(window.nextSdk==='error')return {error:'Existing files are protected.'};
          if(window.nextSdk==='reject')throw new Error('private SDK detail');
          if(window.nextSdk==='hold')await new Promise(resolve=>{window.finishSdk=resolve;});
          return {saved:'<img src=x>.zip',sha256:'c12ab50a808b5266593ef731951a875dd5276a89fd7b963c82eabffbc44d03a7',
            source_sha:'a6eb2c70b4e84cdae5f6d88e788d2fb1f663fa3e'};
        },
      }};
      window.dispatchEvent(new Event('pywebviewready'));
    });
    const settled=()=>page.waitForFunction(()=>document.getElementById('result-panel').getAttribute('aria-busy')==='false');
    const verify=async status=>{
      await page.locator('#verify').click();
      await page.waitForFunction(s=>document.getElementById('status').dataset.state===s,status);
      await settled();
      assert.equal(await page.evaluate(()=>document.activeElement.id),'result-heading');
    };
    const create=async()=>{await page.locator('#create-sample').click();await settled();};

    // Cancel before creation: no evidence or trust magically selected.
    await page.evaluate(()=>window.nextCreate='cancel');await create();
    assert(await page.locator('#verify').isDisabled());
    assert(await page.locator('#sample-details').isHidden());
    assert((await page.locator('#sample-message').textContent()).includes('cancelled'));

    // Built-in sample has no trust by default, including after prior external trust.
    await page.locator('#trust').click();await settled();
    await page.evaluate(()=>window.nextCreate='success');
    await page.locator('#create-sample').focus();await page.keyboard.press('Enter');await settled();
    assert.equal(await page.locator('#log-id').inputValue(),'ets-desktop-synthetic');
    assert.equal(await page.locator('#trust-name').textContent(),'No trust store selected');
    assert.equal(await page.locator('#sample-message img').count(),0);
    assert(!(await page.locator('#sample-details').isHidden()));
    assert.equal(await page.evaluate(()=>window.calls.trust),0);
    assert(await page.locator('[data-format=json]').isDisabled());
    await verify('indeterminate');
    assert.equal(await page.locator('#reason script').count(),0);
    assert.equal(await page.evaluate(()=>window.injected),undefined);
    assert.deepEqual(await page.evaluate(()=>window.calls.verify),['ets-desktop-synthetic']);
    await page.locator('#sample-trust').focus();await page.keyboard.press('Enter');await settled();
    assert(await page.locator('[data-format=json]').isDisabled());
    assert.equal(await page.locator('#raw').textContent(),'No result yet.');
    assert((await page.locator('#trust-name').textContent()).includes('synthetic sample only'));
    await verify('valid');
    for(const format of ['json','markdown','html']){
      await page.locator('[data-format='+format+']').click();await settled();
      assert.equal(await page.locator('#message').textContent(),'Saved report.'+format);
    }
    assert.deepEqual(await page.evaluate(()=>window.calls.reports),['json','markdown','html']);

    // Cancellation and preflight errors preserve a previous usable result and selected sample.
    const previous=await page.locator('#raw').textContent();
    for(const response of ['cancel','error','reject']){
      await page.evaluate(value=>window.nextCreate=value,response);await create();
      assert.equal(await page.locator('#raw').textContent(),previous);
      assert(!(await page.locator('[data-format=json]').isDisabled()));
      assert(!(await page.locator('#sample-trust').isDisabled()));
      assert(!(await page.locator('#sample-message').textContent()).includes('private creation detail'));
    }
    for(const response of ['cancel','error']){
      await page.evaluate(value=>window.nextBundle=value,response);
      await page.locator('#bundle').click();await settled();
      assert.equal(await page.locator('#raw').textContent(),previous);
      assert(!(await page.locator('#sample-details').isHidden()));
    }

    // Repeated clicks cannot create two workspaces or interleave sample/trust/export changes.
    await page.evaluate(()=>window.nextCreate='hold');
    const before=await page.evaluate(()=>window.calls.create);
    await page.locator('#create-sample').click();
    await page.waitForFunction(()=>typeof window.finishCreation==='function');
    for(const id of ['create-sample','bundle','trust','sample-trust','verify','sdk-export','log-id']){
      assert(await page.locator('#'+id).isDisabled(),id+' must be disabled while creating');
    }
    assert(await page.locator('[data-format=json]').isDisabled());
    await page.evaluate(()=>{
      for(let i=0;i<3;i++)document.getElementById('create-sample').dispatchEvent(new Event('click'));
    });
    assert.equal(await page.evaluate(()=>window.calls.create),before+1);
    await page.evaluate(()=>window.finishCreation());await settled();
    assert.equal(await page.locator('#trust-name').textContent(),'No trust store selected');
    assert.equal(await page.locator('#raw').textContent(),'No result yet.');
    await verify('indeterminate');

    // A fresh external bundle cannot inherit the generated sample trust.
    await page.locator('#sample-trust').click();await settled();await verify('valid');
    await page.evaluate(()=>window.nextBundle='success');
    await page.locator('#bundle').click();await settled();
    assert(await page.locator('#sample-details').isHidden());
    assert(await page.locator('#sample-trust').isDisabled());
    assert.equal(await page.locator('#trust-name').textContent(),'No trust store selected');
    assert.equal(await page.locator('#bundle-name img').count(),0);
    assert(await page.locator('[data-format=json]').isDisabled());
    await verify('indeterminate');
    await page.locator('#trust').click();await settled();await verify('valid');
    await page.locator('#log-id').fill('different-log');
    assert(await page.locator('[data-format=json]').isDisabled());
    for(const status of ['invalid','unsupported','malformed','resource_limit']){
      await page.evaluate(value=>window.nextStatus=value,status);await verify(status);
      assert(!(await page.locator('[data-format=json]').isDisabled()));
    }

    // Verification interruption must discard stale success, hide private detail, and recover.
    await page.evaluate(()=>{
      window.previousVerify=window.pywebview.api.verify;
      window.pywebview.api.verify=()=>new Promise((resolve,reject)=>{window.rejectVerification=reject;});
    });
    await page.locator('#verify').click();
    await page.waitForFunction(()=>typeof window.rejectVerification==='function');
    assert(await page.locator('#create-sample').isDisabled());
    assert(await page.locator('#sdk-export').isDisabled());
    await page.evaluate(()=>window.rejectVerification(new Error('private verifier detail')));await settled();
    assert.equal(await page.locator('#status').getAttribute('data-state'),'error');
    assert.equal(await page.locator('#raw').textContent(),'No result yet.');
    assert(await page.locator('[data-format=json]').isDisabled());
    assert(!(await page.locator('#reason').textContent()).includes('private verifier detail'));
    await page.evaluate(()=>{
      window.pywebview.api.verify=async()=>({error:'Verifier could not complete.'});
    });
    await verify('error');
    assert.equal(await page.locator('#reason').textContent(),'Verifier could not complete.');
    await page.evaluate(()=>{window.pywebview.api.verify=window.previousVerify;window.nextStatus='valid';});
    await verify('valid');

    // SDK copy has separate status and never changes the displayed verification snapshot.
    const snapshot=await page.locator('#raw').textContent();
    for(const response of ['cancel','error','reject','success']){
      await page.evaluate(value=>window.nextSdk=value,response);
      await page.locator('#sdk-export').click();await settled();
      assert.equal(await page.locator('#raw').textContent(),snapshot);
      assert(!(await page.locator('#sdk-message').textContent()).includes('private SDK detail'));
      assert.equal(await page.locator('#sdk-message img').count(),0);
    }
    assert((await page.locator('#sdk-message').textContent()).includes('SHA-256: c12ab50a'));
    await page.evaluate(()=>window.nextSdk='hold');
    const sdkBefore=await page.evaluate(()=>window.calls.sdk);
    await page.locator('#sdk-export').click();
    await page.waitForFunction(()=>typeof window.finishSdk==='function');
    assert(await page.locator('#create-sample').isDisabled());
    assert(await page.locator('#verify').isDisabled());
    await page.evaluate(()=>document.getElementById('sdk-export').dispatchEvent(new Event('click')));
    assert.equal(await page.evaluate(()=>window.calls.sdk),sdkBefore+1);
    await page.evaluate(()=>window.finishSdk());await settled();

    // Render an honest synthetic success for screenshot/inspection, then verify narrow layout.
    await page.evaluate(()=>{window.nextCreate='success';window.nextStatus=null;});
    await create();await page.locator('#sample-trust').click();await settled();await verify('valid');
    if(process.env.ETS_UI_SCREENSHOT_DIR){
      await fs.mkdir(process.env.ETS_UI_SCREENSHOT_DIR,{recursive:true});
      await page.screenshot({path:path.join(process.env.ETS_UI_SCREENSHOT_DIR,'developer-wide.png'),fullPage:true});
    }
    await page.setViewportSize({width:640,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
    if(process.env.ETS_UI_SCREENSHOT_DIR){
      await page.screenshot({path:path.join(process.env.ETS_UI_SCREENSHOT_DIR,'developer-narrow.png'),fullPage:true});
    }
    assert.deepEqual(errors,[]);
    console.log('PASS: Developer sample→explicit trust→strict result/reports; SDK export; cancellations; repeated clicks; bridge recovery; escaping; keyboard; narrow layout');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
