#!/usr/bin/env node

import { spawn } from 'child_process';
import { setTimeout as delay } from 'timers/promises';
import path from 'path';

const STORYBOOK_URL = 'http://127.0.0.1:6006/';
const STORYBOOK_BIN = process.platform === 'win32'
  ? path.join('node_modules', '.bin', 'storybook.cmd')
  : path.join('node_modules', '.bin', 'storybook');
const STORYBOOK_ARGS = ['dev', '-p', '6006', '--ci', '--no-open'];
const CHECK_COMMANDS = [
  { args: ['run', 'lint'] },
  { args: ['run', 'test', '--', '--run'] },
  { args: ['run', 'test:ui'], env: { CI: '1', PLAYWRIGHT_HTML_REPORT: 'never' } },
];

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';

function spawnNpm(args, options = {}) {
  const { env, ...rest } = options;
  return spawn(npmCmd, args, {
    cwd: process.cwd(),
    stdio: 'inherit',
    shell: process.platform === 'win32',
    env: { ...process.env, ...env },
    ...rest,
  });
}

async function waitForStorybook(proc) {
  const maxAttempts = 60;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    if (proc.exitCode !== null) {
      throw new Error(`Storybook process exited early with code ${proc.exitCode}`);
    }
    try {
      const response = await fetch(STORYBOOK_URL, { method: 'GET' });
      if (response.ok) {
        return;
      }
    } catch {
      // ignore fetch failures while waiting
    }
    await delay(1000);
  }
  throw new Error(`Timed out waiting for Storybook at ${STORYBOOK_URL}`);
}

async function runCommand(command) {
  const { args, env } = command;
  await new Promise((resolve, reject) => {
    const child = spawnNpm(args, { env });
    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`npm ${args.join(' ')} exited with code ${code}`));
      }
    });
  });
}

async function main() {
  let storybookProcess;
  try {
    console.log('Starting Storybook...');
    storybookProcess = spawn(STORYBOOK_BIN, STORYBOOK_ARGS, {
      cwd: process.cwd(),
      stdio: 'inherit',
      shell: process.platform === 'win32',
    });

    storybookProcess.on('exit', (code) => {
      if (code !== null && code !== 0) {
        console.error(`Storybook process exited with code ${code}`);
      }
    });

    await waitForStorybook(storybookProcess);
    console.log('Storybook is ready. Running UI checks...');

    for (const command of CHECK_COMMANDS) {
      console.log(`\n> npm ${command.args.join(' ')}`);
      await runCommand(command);
    }

    console.log('\n✅ UI checks completed successfully.');
  } catch (error) {
    console.error('\n❌ UI check failed:', error);
    process.exitCode = 1;
  } finally {
    if (storybookProcess && storybookProcess.exitCode === null) {
      storybookProcess.kill();
    }
  }
}

main().catch((error) => {
  console.error('\n❌ Unexpected error:', error);
  process.exit(1);
});
