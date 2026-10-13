"""Run against the synthetic fixture on 18001 and headless Edge CDP on 19229."""
import asyncio
import base64
import json
import time
import urllib.request
from pathlib import Path
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[2]

async def main():
    (ROOT / '.qa' / 'screenshots').mkdir(parents=True, exist_ok=True)
    pages = json.load(urllib.request.urlopen('http://127.0.0.1:19229/json'))
    page = next(page for page in pages if page['type'] == 'page')
    errors = []
    sequence = 0
    async with connect(page['webSocketDebuggerUrl'], max_size=10_000_000) as socket:
        async def command(method, params=None):
            nonlocal sequence
            sequence += 1
            await socket.send(json.dumps(dict(id=sequence, method=method, params=params or {})))
            while True:
                message = json.loads(await socket.recv())
                if message.get('method') == 'Runtime.exceptionThrown': errors.append(message['params']['exceptionDetails'])
                if message.get('id') == sequence:
                    if 'error' in message: raise AssertionError(message['error'])
                    return message.get('result', {})
        async def evaluate(expression):
            result = await command('Runtime.evaluate', dict(expression=expression, returnByValue=True, awaitPromise=True))
            if result.get('exceptionDetails'): raise AssertionError(result['exceptionDetails'])
            return result.get('result', {}).get('value')
        async def wait(expression):
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if await evaluate(expression): return
                await asyncio.sleep(.1)
            raise AssertionError('Timeout: ' + expression)
        async def click(label):
            await evaluate(f"Array.from(document.querySelectorAll('button')).find(button => button.textContent.trim() === {json.dumps(label)}).click()")
        async def fill(selector, value):
            await evaluate(f"(() => {{ const input=document.querySelector({json.dumps(selector)}); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,{json.dumps(value)}); input.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        async def select(key):
            await evaluate(f"(() => {{const input=document.querySelector('#leadSelect');input.value={json.dumps(key)};input.dispatchEvent(new Event('change',{{bubbles:true}}));}})()")
        async def screenshot(name):
            result = await command('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False})
            (ROOT / '.qa' / 'screenshots' / name).write_bytes(base64.b64decode(result['data']))

        await command('Runtime.enable')
        await command('Page.enable')
        await command('Emulation.setDeviceMetricsOverride', dict(width=1440, height=1000, deviceScaleFactor=1, mobile=False))
        await command('Page.navigate', dict(url='http://127.0.0.1:18001'))
        await wait("document.querySelector('.score-number')?.textContent === '8.1'")
        assert await evaluate("fetch('/__test/stats').then(r=>r.json()).then(d=>d.sync_calls===0)")
        assert not await evaluate("/Rajesh|Apex|35 Seats|94%/.test(document.body.innerText)")
        await click('Edit Lead')
        await wait("document.querySelector('dialog[open] input[name=name]') !== null")
        await fill('input[name=name]', 'Saved Buyer')
        await click('Save changes')
        await wait("!document.querySelector('dialog[open]') && document.querySelector('.lead-name-text')?.textContent === 'Saved Buyer'")
        await command('Page.reload')
        await wait("document.querySelector('.lead-name-text')?.textContent === 'Saved Buyer'")
        await click('Edit Lead')
        await fill('input[name=name]', 'Unsaved edit')
        await click('Cancel')
        await click('Edit Lead')
        await wait("document.querySelector('input[name=name]')?.value === 'Saved Buyer'")
        await fill('input[name=name]', 'FAIL')
        await click('Save changes')
        await wait("document.querySelector('dialog')?.innerText.includes('Synthetic save failure')")
        await click('Cancel')
        await click('Sync Battlecard')
        await asyncio.sleep(.2)
        await select('2')
        await wait("document.querySelector('.lead-name-text')?.textContent === 'Test Buyer 2' && document.querySelector('.score-number')?.textContent === '0.0'")
        await asyncio.sleep(1.8)
        assert await evaluate("document.querySelector('.score-number')?.textContent === '0.0'")
        await click('Sync Battlecard')
        await wait("document.body.innerText.includes('Synthetic network failure')")
        assert await evaluate("document.querySelector('.gauge-card') !== null")
        await select('1')
        await wait("document.querySelector('.score-number')?.textContent === '8.1'")
        await screenshot('desktop.png')
        await evaluate("document.querySelector('.header-search-bar').click()")
        await fill('dialog input', '2')
        await wait("document.querySelectorAll('dialog .spotlight-item').length === 1")
        await evaluate("document.querySelector('dialog .spotlight-item').click()")
        await wait("document.querySelector('.lead-name-text')?.textContent === 'Test Buyer 2'")
        await click('Edit Lead')
        assert await evaluate("document.querySelector('input[name=name]').value === 'Test Buyer 2'")
        await click('Cancel')
        await command('Emulation.setDeviceMetricsOverride', dict(width=390, height=844, deviceScaleFactor=1, mobile=True))
        await screenshot('mobile.png')
        assert await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Horizontal overflow on mobile'
        await evaluate("document.querySelector('.btn-toggle-sidebar').click()")
        await click('Reports')
        await wait("document.body.innerText.includes('Download JSON report')")
        assert not errors, errors
        print('Browser checks passed: real save/reload flow, failed save, fresh modal state, zero score, lead-switch race, analysis error, search, mobile layout and report navigation.')
        print('Screenshots: .qa/screenshots/desktop.png and mobile.png')
        await command('Browser.close')

if __name__ == '__main__': asyncio.run(main())
