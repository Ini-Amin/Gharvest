#!/usr/bin/env python3
"""Otomasi signup Google via raw CDP (websocket) — kompatibel Chrome 83 Android 11."""
import json, time, random, sys, websocket
sys.path.insert(0, '/home/amen/Auto-FreeCF/scripts')

CDP_HTTP = 'http://127.0.0.1:9222'

def get_ws_url():
    import urllib.request
    tabs = json.load(urllib.request.urlopen(CDP_HTTP + '/json'))
    for t in tabs:
        if t.get('type') == 'page' and 'google' in t.get('url', ''):
            return t['webSocketDebuggerUrl']
    return tabs[0]['webSocketDebuggerUrl'] if tabs else None

class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.id = 0
    def cmd(self, method, **params):
        self.id += 1
        self.ws.send(json.dumps({'id': self.id, 'method': method, 'params': params}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get('id') == self.id:
                return r.get('result', {})
    def js(self, expr):
        r = self.cmd('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=True)
        return r.get('result', {}).get('value')
    def type_js(self, sel, text):
        # Human-like typing via JS dengan delay
        expr = f"""
        (async () => {{
            const el = document.querySelector('{sel}');
            if (!el) return 'NOT_FOUND';
            el.focus(); el.value = '';
            for (const c of `{text}`) {{
                el.value += c;
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                await new Promise(r => setTimeout(r, {random.randint(50, 140)}));
            }}
            el.dispatchEvent(new Event('change', {{bubbles: true}}));
            return 'OK:' + el.value;
        }})()
        """
        return self.js(expr)

def main():
    ws = get_ws_url()
    print('WS:', ws[:70])
    c = CDP(ws)
    url = c.js('location.href')
    print('URL:', url[:80])

    # Cek step saat ini
    has_gender = c.js("!!document.querySelector('select#gender')")
    has_username = c.js("!!document.querySelector('input#username')")
    has_passwd = c.js("!!document.querySelector('input[name=Passwd]')")
    print(f"gender={has_gender} username={has_username} passwd={has_passwd}")

    if has_gender:
        print('→ Pilih Gender Male')
        c.js("document.querySelector('select#gender').value='Male';"
             "document.querySelector('select#gender').dispatchEvent(new Event('change',{bubbles:true}));'OK'")
        time.sleep(1)
        c.js("[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Next')).click();'clicked'")
        time.sleep(6)

    if has_username:
        from persona import username as gen_user
        uname = gen_user().lower().replace('_','').replace('.','')[:18]
        print('→ Username:', uname)
        print(c.type_js('input#username', uname))
        time.sleep(1)
        c.js("[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Next')).click();'clicked'")
        time.sleep(6)

    if has_passwd:
        print('→ Password')
        import os
        PW = os.environ.get('FARM_PW', 'Kanca2026!xQ')
        c.type_js('input[name="Passwd"]', PW)
        c.type_js('input[name="ConfirmPasswd"]', PW)
        time.sleep(1)
        c.js("[...document.querySelectorAll('button')].find(b=>b.textContent.includes('Next')).click();'clicked'")
        time.sleep(6)

    print('URL akhir:', (c.js('location.href') or '')[:80])
    # Screenshot via CDP
    r = c.cmd('Page.captureScreenshot', format='png')
    import base64
    open('/tmp/cdp_final.png','wb').write(base64.b64decode(r['data']))
    print('Screenshot: /tmp/cdp_final.png')

if __name__ == '__main__':
    main()
