const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
  const handlers = {};
  const formHandlers = {};
  const timers = new Map();
  const visits = [];
  let submissions = 0;
  let now = 0;
  let sequence = 0;
  const form = { dataset: {}, submit() { submissions++; }, addEventListener(type, handler) { formHandlers[type] = handler; } };
  const card = { dataset: { detailUrl: '/events/1' }, querySelector() { return form; }, addEventListener(type, handler) { handlers[type] = handler; } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../eventhub/static/app.js'), 'utf8'), {
    document: { querySelectorAll(selector) { return selector === '.event-card' ? [card] : []; } },
    window: {
      location: { assign(url) { visits.push(url); } },
      setTimeout(callback, delay) { const identifier = ++sequence; timers.set(identifier, { callback, due: now + delay }); return identifier; },
      clearTimeout(identifier) { timers.delete(identifier); },
    },
  });
  return {
    visits, formHandlers, form,
    get submissions() { return submissions; },
    event(options = {}) { return { detail: 1, preventDefault() {}, target: { closest() { return null; } }, ...options }; },
    fire(type, event) { handlers[type](event); },
    advance(duration) {
      now += duration;
      for (const [identifier, timer] of timers) {
        if (timer.due <= now) { timers.delete(identifier); timer.callback(); }
      }
    },
  };
}

test('single click navigates after the double-click window', () => {
  const browser = setup();
  browser.fire('click', browser.event());
  browser.advance(601);
  assert.deepEqual(browser.visits, ['/events/1']);
  assert.equal(browser.submissions, 0);
});

test('400ms double click buys once without navigating', () => {
  const browser = setup();
  browser.fire('click', browser.event());
  browser.advance(400);
  browser.fire('click', browser.event({ detail: 2 }));
  browser.fire('dblclick', browser.event());
  browser.fire('dblclick', browser.event());
  browser.advance(601);
  assert.deepEqual(browser.visits, []);
  assert.equal(browser.submissions, 1);
});

test('modified clicks and keyboard links keep native behavior', () => {
  const browser = setup();
  const fail = () => assert.fail('native action must not be prevented');
  browser.fire('click', browser.event({ ctrlKey: true, preventDefault: fail }));
  browser.fire('click', browser.event({ detail: 0, target: { closest(selector) { return selector === 'a'; } }, preventDefault: fail }));
  browser.advance(601);
  assert.deepEqual(browser.visits, []);
});

test('explicit buy control avoids navigation and rejects repeat submission', () => {
  const browser = setup();
  browser.fire('click', browser.event({ target: { closest() { return true; } }, preventDefault() { assert.fail(); } }));
  browser.formHandlers.submit(browser.event());
  let prevented = false;
  browser.formHandlers.submit(browser.event({ preventDefault() { prevented = true; } }));
  browser.advance(601);
  assert.equal(prevented, true);
  assert.deepEqual(browser.visits, []);
});
