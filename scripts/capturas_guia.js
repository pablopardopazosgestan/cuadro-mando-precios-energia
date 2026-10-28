// Capturas del panel publicado para la guía de usuario (docs/guia/*.png). Requiere Node y Playwright con Chromium:
//   node scripts/capturas_guia.js   (tras `python -m precios panel`)
const { chromium } = require('playwright');
const http = require('http'); const fs = require('fs'); const path = require('path');
const raiz = path.resolve(__dirname, '..', 'sitio'); const out = path.resolve(__dirname, '..', 'docs', 'guia') + '/';
const tipos = { '.json': 'application/json', '.js': 'application/javascript', '.html': 'text/html; charset=utf-8' };
const srv = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0].split('#')[0]); const f = path.join(raiz, u === '/' ? '/index.html' : u);
  fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { 'Content-Type': tipos[path.extname(f)] || 'application/octet-stream' }); res.end(d); });
}).listen(8768);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1.5 });
  const shot = async (sel, nombre, pad = 0) => { const el = await page.$(sel); await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(400); await el.screenshot({ path: out + nombre }); };
  await page.goto('http://127.0.0.1:8768/#series=gasoleo_c,pellet_saco,tur2,butano&desde=2023-01-01&hasta=2026-10-27&frecuencia=original', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: out + '01_portada.png', clip: { x: 0, y: 0, width: 1200, height: 560 } });
  await shot('#tarjetas', '02_tarjetas.png');
  await shot('#seccion-resumen .dos-col', '03_ranking_claves.png');
  await shot('#tabla-resumen', '04_tabla.png');
  await shot('#seccion-comparativo .panel-controles', '05_controles.png');
  await shot('#g-comparativo', '06_comparativo.png');
  // Base 100 + media móvil con conjunto energía final
  await page.click('button[data-conjunto="final"]'); await page.check('#o-base100'); await page.waitForTimeout(1200);
  await shot('#g-comparativo', '07_base100.png');
  await page.uncheck('#o-base100');
  // Indicadores: impuestos y ver datos en TUR 2
  await page.check('#o-impuestos'); await page.waitForTimeout(800);
  await page.click('#card-tur2 button[data-v="datos"]'); await page.waitForTimeout(600);
  await shot('#card-tur2', '08_indicador_tur2.png');
  await shot('#seccion-individuales .grid', '09_indicadores.png');
  await shot('#seccion-estado', '10_estado.png');
  // móvil
  const movil = await browser.newPage({ viewport: { width: 390, height: 800 }, deviceScaleFactor: 2 });
  await movil.goto('http://127.0.0.1:8768/', { waitUntil: 'networkidle' }); await movil.waitForTimeout(2000);
  await movil.screenshot({ path: out + '11_movil.png', clip: { x: 0, y: 0, width: 390, height: 800 } });
  await browser.close(); srv.close();
  console.log(fs.readdirSync(out));
})();
