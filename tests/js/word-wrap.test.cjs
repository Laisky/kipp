'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createRequire } = require('node:module');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { createHash } = require('node:crypto');

const root = process.env.KIPP_QUALIFICATION_ROOT || path.resolve(__dirname, '../..');
const fromRoot = createRequire(path.join(root, 'package.json'));
const adapterPath = fromRoot.resolve('cz-conventional-changelog');
const fromAdapter = createRequire(adapterPath);
const wrap = fromAdapter('word-wrap');
const version = fromAdapter('word-wrap/package.json').version;
const options = { width: 100, indent: '', newline: '\n', trim: true };

async function commit(answers, observe = () => {}) {
  const original = console.log;
  console.log = () => {};
  try {
    return await new Promise((resolve) => {
      fromRoot('cz-conventional-changelog').prompter({
        prompt(questions) {
          observe(questions);
          return Promise.resolve(answers);
        },
      }, resolve);
    });
  } finally {
    console.log = original;
  }
}

function boundedAdapter(body) {
  const script = `
    console.log = () => {};
    const adapter = require(${JSON.stringify(adapterPath)});
    const body = process.argv[1] === 'hostile'
      ? 'a' + ' '.repeat(500000) + '\\u00a0'
      : 'a' + ' '.repeat(50000) + 'b';
    adapter.prompter({prompt: () => Promise.resolve({
      type:'feat', scope:'', subject:'bounded', body, footer:''
    })}, message => process.stdout.write(JSON.stringify({
      bytes:Buffer.byteLength(message),
      sha256:require('node:crypto').createHash('sha256').update(message).digest('hex')
    })));
  `;
  const result = spawnSync(process.execPath, ['-e', script, body], {
    cwd: root,
    timeout: 2000,
    maxBuffer: 64 * 1024,
    encoding: 'utf8',
  });
  assert.ifError(result.error);
  assert.equal(result.signal, null);
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

function messageIdentity(message) {
  return {
    bytes: Buffer.byteLength(message),
    sha256: createHash('sha256').update(message).digest('hex'),
  };
}

test('the adapter resolves the expected locked word-wrap', () => {
  assert.equal(version, process.env.EXPECTED_WORD_WRAP_VERSION || '1.2.4');
  assert.equal(fromAdapter.resolve('word-wrap'), fromRoot.resolve('word-wrap'));
});

test('null and undefined inputs retain their values', () => {
  assert.equal(wrap(null, options), null);
  assert.equal(wrap(undefined, options), undefined);
});

test('explicit wrapping preserves normal text', () => {
  assert.equal(wrap('alpha beta gamma', { ...options, width: 10 }), 'alpha beta\ngamma');
});

test('explicit indent and newline remain supported', () => {
  assert.equal(wrap('alpha beta gamma', { width: 10, indent: '>', newline: '|', trim: true }), '>alpha beta |gamma');
});

test('spaces and tabs are trimmed at line ends', () => {
  assert.equal(wrap('alpha  \nbeta\t\t', options), 'alpha\nbeta');
});

test('nonbreaking space and preceding spaces remain content', () => {
  assert.equal(wrap('a   \u00a0', options), 'a   \u00a0');
});

test('explicit cut behavior is preserved', () => {
  assert.equal(wrap('abcdef', { ...options, width: 3, cut: true }), 'abc\ndef');
});

test('upstream default-indent change is explicit rather than hidden', () => {
  assert.equal(wrap('alpha'), version === '1.2.2' ? '  alpha' : 'alpha');
});

test('actual prompter preserves scope, subject, body and footer', async () => {
  assert.equal(await commit({ type: 'fix', scope: ' cli ', subject: ' preserve text ', body: 'alpha beta', footer: 'Refs #123' }),
    'fix(cli): preserve text\n\nalpha beta\n\nRefs #123');
});

test('empty scope, body and footer retain existing message shape', async () => {
  assert.equal(await commit({ type: 'docs', scope: ' ', subject: ' clarify ', body: '', footer: '' }), 'docs: clarify\n\n\n\n');
});

test('the existing 100-character header limit remains unchanged', async () => {
  const message = await commit({ type: 'feat', scope: '', subject: 'x'.repeat(150), body: '', footer: '' });
  assert.equal(message.split('\n')[0], ('feat: ' + 'x'.repeat(150)).slice(0, 100));
});

test('real prompt questions and commit-type choices remain available', async () => {
  await commit({ type: 'test', scope: '', subject: 'fixture', body: '', footer: '' }, (questions) => {
    assert.deepEqual(questions.map(q => q.name), ['type', 'scope', 'subject', 'body', 'footer']);
    assert.ok(questions[0].choices.some(c => c.value === 'fix'));
    assert.ok(questions[0].choices.some(c => c.value === 'feat'));
  });
});

test('bounded ordinary-whitespace control completes with exact adapter output', () => {
  assert.deepEqual(boundedAdapter('ordinary'), messageIdentity('feat: bounded\n\na\nb\n\n'));
});

test('nonbreaking-space trim regression completes without losing adapter content', () => {
  const body = 'a' + ' '.repeat(500000) + '\u00a0';
  assert.deepEqual(boundedAdapter('hostile'), messageIdentity('feat: bounded\n\n' + body + '\n\n'));
});

