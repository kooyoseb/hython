"use strict";

const path = require("path");
const fs = require("fs");
const os = require("os");
const {runTests} = require("@vscode/test-electron");

async function main() {
  const extensionDevelopmentPath = path.resolve(__dirname, "..");
  const extensionTestsPath = path.resolve(__dirname, "suite", "index");
  const workspacePath = path.resolve(__dirname, "fixtures");
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), "hython-vscode-test-"));
  const vscodeExecutablePath = process.env.VSCODE_EXECUTABLE_PATH
    || "T:\\Microsoft VS Code\\Code.exe";
  try {
    await runTests({
      vscodeExecutablePath,
      extensionDevelopmentPath,
      extensionTestsPath,
      launchArgs: [
        workspacePath,
        "--disable-extensions",
        "--user-data-dir",
        userDataDir
      ]
    });
  } finally {
    await new Promise(resolve => setTimeout(resolve, 750));
    try {
      fs.rmSync(userDataDir, {
        recursive: true,
        force: true,
        maxRetries: 10,
        retryDelay: 250
      });
    } catch (error) {
      console.warn(`테스트 임시 폴더는 다음 정리 때 제거됩니다: ${error.message}`);
    }
  }
}

main().catch(error => {
  console.error("Hython VS Code 통합 테스트 실패");
  console.error(error);
  process.exit(1);
});
