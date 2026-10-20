import tempfile
import unittest
from pathlib import Path

from mcstats.server import index_html, site_version


class VersionTest(unittest.TestCase):
    def test_every_script_gets_the_version(self):
        with tempfile.TemporaryDirectory() as d:
            web = Path(d)
            (web / "js").mkdir(); (web / "css").mkdir(); (web / "i18n").mkdir()
            (web / "js" / "main.js").write_text("import './util.js';")
            (web / "js" / "util.js").write_text("export const a = 1;")
            (web / "css" / "style.css").write_text("body {}")
            (web / "index.html").write_text('<head>\n<link rel="stylesheet" href="/css/style.css">\n'
                                            '<script type="module" src="/js/main.js"></script>')
            v = site_version(web)
            html = index_html(web).decode()
            self.assertIn(f'href="/css/style.css?v={v}"', html)
            self.assertIn(f'src="/js/main.js?v={v}"', html)
            self.assertIn(f'"/js/util.js":"/js/util.js?v={v}"', html)  # imports inside modules too
            self.assertLess(html.index("importmap"), html.index("<link"))
            (web / "js" / "util.js").write_text("export const a = 2;")
            self.assertNotEqual(site_version(web), v)


if __name__ == "__main__":
    unittest.main()
