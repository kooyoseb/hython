"use strict";

const assert = require("assert");
const path = require("path");
const vscode = require("vscode");

const extensionRoot = path.resolve(__dirname, "..", "..");
const repositoryRoot = path.resolve(extensionRoot, "..");
const engine = path.join(repositoryRoot, "release", "hython.exe");
const fixture = vscode.Uri.file(
  path.join(extensionRoot, "test", "fixtures", "main.hy")
);
const completionFixture = vscode.Uri.file(
  path.join(extensionRoot, "test", "fixtures", "completion.hy")
);

async function check(name, action) {
  process.stdout.write(`  확인: ${name} ... `);
  await action();
  process.stdout.write("통과\n");
}

async function runTests() {
  await vscode.workspace.getConfiguration("hython").update(
    "executablePath",
    engine,
    vscode.ConfigurationTarget.Global
  );
  const extension = vscode.extensions.getExtension(
    "kooyoseb.hython-development"
  );
  assert.ok(extension, "확장이 Extension Host에 로드되어야 합니다.");
  await extension.activate();

  await check(".hy 파일을 Hython 언어로 인식한다", async () => {
    const document = await vscode.workspace.openTextDocument(fixture);
    assert.strictEqual(document.languageId, "hython");
  });

  await check("Hython 엔진 자동완성을 반환한다", async () => {
    const document = await vscode.workspace.openTextDocument(completionFixture);
    const items = await vscode.commands.executeCommand(
      "vscode.executeCompletionItemProvider",
      document.uri,
      new vscode.Position(0, 2)
    );
    assert.ok(items.items.some(item => item.label === "프린트"));
  });

  await check("함수 호출에서 정의로 이동한다", async () => {
    const document = await vscode.workspace.openTextDocument(fixture);
    const definitions = await vscode.commands.executeCommand(
      "vscode.executeDefinitionProvider",
      document.uri,
      new vscode.Position(3, 6)
    );
    assert.ok(definitions.length >= 1);
    assert.strictEqual(definitions[0].range.start.line, 0);
  });

  await check("참조·호버·이름 변경 공급자가 실제 결과를 반환한다", async () => {
    const document = await vscode.workspace.openTextDocument(fixture);
    const position = new vscode.Position(3, 6);
    const references = await vscode.commands.executeCommand(
      "vscode.executeReferenceProvider",
      document.uri,
      position
    );
    assert.ok(references.length >= 2);
    const hovers = await vscode.commands.executeCommand(
      "vscode.executeHoverProvider",
      document.uri,
      position
    );
    assert.ok(hovers.length >= 1);
    const rename = await vscode.commands.executeCommand(
      "vscode.executeDocumentRenameProvider",
      document.uri,
      position,
      "합계"
    );
    assert.ok(rename.entries().length >= 1);
  });

  await check("중단점에서 정지하고 지역 변수를 조회한다", async () => {
    const folder = vscode.workspace.getWorkspaceFolder(fixture);
    vscode.debug.addBreakpoints([
      new vscode.SourceBreakpoint(
        new vscode.Location(fixture, new vscode.Position(4, 0))
      )
    ]);
    let session;
    const startedSession = new Promise(resolve => {
      const disposable = vscode.debug.onDidStartDebugSession(value => {
        if (value.type === "hython") {
          session = value;
          disposable.dispose();
          resolve(value);
        }
      });
    });
    const stopped = new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error("Hython 중단점 정지 시간 초과")),
        20000
      );
      const tracker = vscode.debug.registerDebugAdapterTrackerFactory(
        "hython",
        {
          createDebugAdapterTracker() {
            return {
              onDidSendMessage(message) {
                if (message.type === "event" && message.event === "stopped") {
                  clearTimeout(timeout);
                  tracker.dispose();
                  resolve(message);
                }
              }
            };
          }
        }
      );
    });
    const terminated = new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error("Hython 디버그 세션 종료 시간 초과")),
        20000
      );
      const disposable = vscode.debug.onDidTerminateDebugSession(session => {
        if (session.type === "hython") {
          clearTimeout(timeout);
          disposable.dispose();
          resolve();
        }
      });
    });
    const started = await vscode.debug.startDebugging(folder, {
      type: "hython",
      request: "launch",
      name: "통합 테스트",
      program: fixture.fsPath
    });
    assert.strictEqual(started, true);
    await startedSession;
    await stopped;
    const threads = await session.customRequest("threads");
    const stack = await session.customRequest("stackTrace", {
      threadId: threads.threads[0].id
    });
    assert.strictEqual(stack.stackFrames[0].line, 5);
    const scopes = await session.customRequest("scopes", {
      frameId: stack.stackFrames[0].id
    });
    const variables = await session.customRequest("variables", {
      variablesReference: scopes.scopes[0].variablesReference
    });
    assert.ok(variables.variables.some(item => item.name === "결과"));
    await session.customRequest("continue", {threadId: 1});
    await terminated;
    vscode.debug.removeBreakpoints(vscode.debug.breakpoints);
  });
}

module.exports = {runTests};
