import fs from 'node:fs';

const outputDir = 'docs/images/user-guide';
const chromeDebugUrl = 'http://127.0.0.1:9223';
const appUrl = 'http://127.0.0.1:5174';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

let nextId = 0;
let ws;
const pending = new Map();

async function json(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  return send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
}

async function screenshot(filename) {
  const result = await send('Page.captureScreenshot', {
    format: 'png',
    captureBeyondViewport: false,
  });
  fs.writeFileSync(`${outputDir}/${filename}`, Buffer.from(result.data, 'base64'));
  console.log(`saved ${filename}`);
}

async function clickText(text) {
  const expression = `(() => {
    const elements = [...document.querySelectorAll('button,a,[role=button],.cds--side-nav__link')];
    const target = elements.find((element) =>
      (element.innerText || element.textContent || '').trim().includes(${JSON.stringify(text)})
    );
    if (!target) return 'missing ${text}';
    target.click();
    return 'clicked ' + (target.innerText || target.textContent || '').trim();
  })()`;
  const result = await evaluate(expression);
  console.log(result.result?.value);
  await sleep(900);
}

async function clickSideNav(text) {
  const expression = `(() => {
    const elements = [...document.querySelectorAll('.cds--side-nav__link, .cds--side-nav a, a')];
    const target = elements.find((element) =>
      (element.innerText || element.textContent || '').trim().includes(${JSON.stringify(text)})
    );
    if (!target) return 'missing nav ${text}';
    target.click();
    return 'clicked nav ' + (target.innerText || target.textContent || '').trim();
  })()`;
  const result = await evaluate(expression);
  console.log(result.result?.value);
  await sleep(900);
}

async function setProjectSearch(value) {
  await evaluate(`(() => {
    const input = document.querySelector('#project-browser-search');
    if (!input) return 'missing search';
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(input, ${JSON.stringify(value)});
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return 'searched ${value}';
  })()`);
  await sleep(700);
}

async function scrollHeadingIntoView(text) {
  await evaluate(`(() => {
    const headings = [...document.querySelectorAll('h1,h2,h3,h4')];
    const heading = headings.find((element) => (element.textContent || '').includes(${JSON.stringify(text)}));
    if (heading) heading.scrollIntoView({ block: 'start' });
  })()`);
  await sleep(700);
}

async function openSeededProject() {
  await clickText('Projects');
  await clickText('sample-healthcare');
  await clickText('medical-imaging-dr');
  await sleep(1800);
}

async function connectToChrome() {
  const tabs = await json(`${chromeDebugUrl}/json/list`);
  const tab = tabs.find((candidate) => candidate.type === 'page') || tabs[0];
  if (!tab?.webSocketDebuggerUrl) {
    throw new Error('No Chrome debugging page target found.');
  }

  ws = new WebSocket(tab.webSocketDebuggerUrl);
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const callbacks = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) callbacks.reject(new Error(message.error.message));
      else callbacks.resolve(message.result || {});
    }
  };
  await new Promise((resolve) => {
    ws.onopen = resolve;
  });
}

async function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  await connectToChrome();

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 1000,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await send('Page.navigate', { url: appUrl });
  await sleep(2500);

  await clickText('Projects');
  await setProjectSearch('sample');
  await screenshot('02-projects-workspace.png');

  await openSeededProject();
  await clickSideNav('Upload');
  await screenshot('03-upload-source-files.png');

  await clickSideNav('Review model');
  await screenshot('04-review-model.png');

  await clickSideNav('Questions');
  await screenshot('05-design-questions.png');

  await clickSideNav('Review model');
  await scrollHeadingIntoView('Architecture Advisor');
  await screenshot('06-architecture-advisor.png');

  await clickSideNav('Diagram');
  await screenshot('07-generate-diagrams.png');

  await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')]
      .find((element) => (element.innerText || '').includes('Analyze quality')
        || (element.innerText || '').includes('Analyze diagram quality'));
    if (button) button.click();
  })()`);
  await sleep(2500);
  await screenshot('08-quality-analyzer.png');

  await clickText('Projects');
  await screenshot('09-project-activity.png');

  await evaluate(`(() => {
    const buttons = [...document.querySelectorAll('button')];
    const button = buttons.find((element) => (element.innerText || '').includes('Preview restore'))
      || buttons.find((element) => (element.innerText || '').includes('Restore'));
    if (button) button.click();
    return button ? (button.innerText || 'clicked') : 'no restore button';
  })()`);
  await sleep(1200);
  await screenshot('10-restore-preview.png');

  await evaluate(`(() => {
    const button = [...document.querySelectorAll('button')]
      .find((element) => (element.innerText || '').includes('Cancel')
        || (element.getAttribute('aria-label') || '').toLowerCase().includes('close'));
    if (button) button.click();
  })()`);
  await sleep(600);
  await screenshot('11-export-package.png');

  ws.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
