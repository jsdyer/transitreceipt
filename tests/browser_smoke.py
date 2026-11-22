"""Exercise source data, filtering, evidence downloads and mobile layout in CI."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,shutil,tempfile,threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
def main():
    slug=json.loads((ROOT/'tool.json').read_text())['id'];shots=ROOT/'browser-checks';shots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        shutil.copytree(ROOT/'dist',Path(temp)/slug)
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=temp));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/{slug}/');page.locator('#receipt option').first.wait_for(state='attached');page.locator('#rows tr').first.wait_for()
                assert page.locator('#chart svg').count()==1
                page.select_option('#filter','pending');page.select_option('#filter','all')
                with page.expect_download() as info:page.click('#export')
                download=info.value;assert download.suggested_filename.endswith('.csv')
                entities=page.locator('#entity option').count()
                if entities>1:page.select_option('#entity',index=1);assert page.locator('#rows tr').count()>0
                page.screenshot(path=str(shots/'desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');page.screenshot(path=str(shots/'mobile.png'),full_page=True)
                assert not errors,errors;browser.close()
        finally:server.shutdown()
if __name__=='__main__':main()
