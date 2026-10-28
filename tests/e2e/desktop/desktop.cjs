const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1100,height:850}});
    const errors=[];
    page.on('pageerror', error=>errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(__dirname,'../../../ets/desktop/index.html')).href);
    assert(await page.locator('#bundle').isDisabled());
    await page.evaluate(()=>{
      window.calls=[];
      window.nextStatus='indeterminate';
      window.pywebview={api:{
        select_bundle:async()=>({name:'<img src=x onerror=alert(1)>.json',selected:true}),
        select_trust:async()=>({name:'trust.json',selected:true}),
        verify:async()=>({outcome:{status:window.nextStatus,valid:window.nextStatus==='valid',
          reason:'<script>window.injected=true</script>',standing_status:'checkpoint_only',
          checks:[{passed:false,reason:'Key not in trusted store'}]}}),
        export_report:async(format)=>{window.calls.push(format);return {saved:'report.'+format};},
      }};
      window.dispatchEvent(new Event('pywebviewready'));
    });
    await page.locator('#bundle').click();
    await page.locator('#verify').waitFor({state:'visible'});
    assert.equal(await page.locator('#bundle-name img').count(),0);
    for(const status of ['indeterminate','invalid','unsupported','malformed','resource_limit','valid']){
      await page.evaluate(s=>window.nextStatus=s,status);
      await page.locator('#verify').click();
      await page.waitForFunction(s=>document.getElementById('status').dataset.state===s,status);
      assert.equal(await page.locator('#reason script').count(),0);
      assert.equal(await page.evaluate(()=>window.injected),undefined);
      await page.locator('[data-format=json]').click();
      await page.waitForFunction(()=>document.getElementById('message').textContent==='Saved report.json');
    }
    assert.equal(await page.evaluate(()=>window.calls.length),6);
    await page.locator('#log-id').fill('new-log');
    assert(await page.locator('[data-format=json]').isDisabled());
    await page.setViewportSize({width:640,height:900});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
    assert.deepEqual(errors,[]);
    console.log('PASS: desktop UI outcomes, exports, stale-result clearing, escaping, and narrow layout');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
