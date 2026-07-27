"use strict";

const vscode = require("vscode");
const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");
const {HythonDebugAdapter} = require("./debugAdapter");

const LANGUAGE = "hython";
const diagnostics = vscode.languages.createDiagnosticCollection("hython");
const output = vscode.window.createOutputChannel("Hython");
const timers = new Map();
const RESERVED_WORDS = new Set(
  "앤드 애즈 어설트 어싱크 어웨이트 브레이크 케이스 클래스 컨티뉴 데프 델 "
  + "엘리프 엘스 익셉트 파이널리 포 프롬 글로벌 이프 인폴트 임포트 인 이즈 "
  + "람다 매치 논로컬 낫 오어 패스 레이즈 리턴 트라이 와일 위드 일드 타입 "
  + "트루 폴스 넌 널".split(" ")
);
let cachedEngine;
let status;

function configuration() {
  return vscode.workspace.getConfiguration("hython");
}

function workspaceDirectory(document) {
  return vscode.workspace.getWorkspaceFolder(document.uri)?.uri.fsPath
    || path.dirname(document.uri.fsPath);
}

function engineCandidates(document) {
  const configured = configuration().get("executablePath", "").trim();
  const candidates = [];
  if (configured) {
    candidates.push(configured);
  }
  if (document) {
    const root = workspaceDirectory(document);
    candidates.push(
      path.join(root, "release", "hython.exe"),
      path.join(root, "hython.exe")
    );
  }
  candidates.push("hython.exe", "hython");
  return [...new Set(candidates)];
}

function spawn(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const process = childProcess.spawn(command, args, {
      cwd: options.cwd,
      windowsHide: true,
      shell: false,
      env: {...global.process.env, PYTHONUTF8: "1"}
    });
    let stdout = "";
    let stderr = "";
    process.stdout.setEncoding("utf8");
    process.stderr.setEncoding("utf8");
    process.stdout.on("data", data => { stdout += data; });
    process.stderr.on("data", data => { stderr += data; });
    process.on("error", reject);
    process.on("close", code => resolve({code, stdout, stderr}));
    if (options.input !== undefined) {
      process.stdin.setDefaultEncoding("utf8");
      process.stdin.end(options.input);
    }
  });
}

async function findEngine(document, refresh = false) {
  if (!refresh && cachedEngine) {
    return cachedEngine;
  }
  for (const candidate of engineCandidates(document)) {
    if (
      (candidate.includes("\\") || candidate.includes("/"))
      && !fs.existsSync(candidate)
    ) {
      continue;
    }
    try {
      const result = await spawn(candidate, ["--version"], {
        cwd: document ? workspaceDirectory(document) : undefined
      });
      if (result.code === 0) {
        cachedEngine = candidate;
        status.text = "$(check) Hython";
        status.tooltip = `${(result.stdout || result.stderr).trim()}\n${candidate}`;
        return candidate;
      }
    } catch {
      // 다음 후보를 확인한다.
    }
  }
  status.text = "$(warning) Hython 없음";
  status.tooltip = "Hython 엔진 경로를 선택하세요.";
  return undefined;
}

function jsonPayload(text) {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end < start) {
    throw new Error("Hython 분석 JSON을 찾을 수 없습니다.");
  }
  return JSON.parse(text.slice(start, end + 1));
}

async function analyze(document, position, token) {
  if (document.languageId !== LANGUAGE || token?.isCancellationRequested) {
    return undefined;
  }
  const engine = await findEngine(document);
  if (!engine || token?.isCancellationRequested) {
    return undefined;
  }
  const line = (position?.line ?? 0) + 1;
  const column = position?.character ?? 0;
  const result = await spawn(
    engine,
    [
      "ide", "analyze", document.uri.fsPath, "--stdin",
      "--line", String(line), "--column", String(column)
    ],
    {cwd: workspaceDirectory(document), input: document.getText()}
  );
  if (result.code !== 0) {
    throw new Error((result.stderr || result.stdout).trim());
  }
  return jsonPayload(result.stdout);
}

function severity(value) {
  if (value === "warning") {
    return vscode.DiagnosticSeverity.Warning;
  }
  if (value === "info") {
    return vscode.DiagnosticSeverity.Information;
  }
  return vscode.DiagnosticSeverity.Error;
}

async function refreshDiagnostics(document) {
  if (
    document.languageId !== LANGUAGE
    || !configuration().get("analysis.enabled", true)
  ) {
    diagnostics.delete(document.uri);
    return;
  }
  try {
    const result = await analyze(document, undefined);
    if (!result) {
      return;
    }
    const items = (result.diagnostics || []).map(item => {
      const startLine = Math.max(0, (item.line || 1) - 1);
      const startColumn = Math.max(0, item.column || 0);
      const endLine = Math.max(startLine, (item.endLine || item.line || 1) - 1);
      const endColumn = Math.max(
        startLine === endLine ? startColumn + 1 : 0,
        item.endColumn || startColumn + 1
      );
      const diagnostic = new vscode.Diagnostic(
        new vscode.Range(startLine, startColumn, endLine, endColumn),
        item.message,
        severity(item.severity)
      );
      diagnostic.source = "Hython";
      return diagnostic;
    });
    diagnostics.set(document.uri, items);
  } catch (error) {
    output.appendLine(`[분석 실패] ${document.uri.fsPath}\n${error.message}`);
  }
}

function scheduleDiagnostics(document) {
  const key = document.uri.toString();
  clearTimeout(timers.get(key));
  const delay = configuration().get("analysis.delay", 350);
  timers.set(key, setTimeout(() => {
    timers.delete(key);
    refreshDiagnostics(document);
  }, delay));
}

function completionKind(kind) {
  const kinds = {
    "키워드": vscode.CompletionItemKind.Keyword,
    "내장": vscode.CompletionItemKind.Function,
    "라이브러리": vscode.CompletionItemKind.Module,
    "특수 이름": vscode.CompletionItemKind.Variable,
    "설치 패키지": vscode.CompletionItemKind.Module,
    "런타임": vscode.CompletionItemKind.Reference
  };
  return kinds[kind] || vscode.CompletionItemKind.Text;
}

function symbolKind(kind) {
  if (kind === "클래스") {
    return vscode.SymbolKind.Class;
  }
  if (kind === "비동기 함수") {
    return vscode.SymbolKind.Function;
  }
  return vscode.SymbolKind.Function;
}

function wordAt(document, position) {
  const range = document.getWordRangeAtPosition(
    position,
    /[A-Za-z_가-힣][\w가-힣]*/
  );
  return range ? {range, text: document.getText(range)} : undefined;
}

function escapedRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function identifierRanges(document, identifier) {
  const pattern = new RegExp(
    `(?<![\\w가-힣])${escapedRegExp(identifier)}(?![\\w가-힣])`,
    "gu"
  );
  const text = document.getText();
  const ranges = [];
  for (const match of text.matchAll(pattern)) {
    const start = document.positionAt(match.index);
    const end = document.positionAt(match.index + match[0].length);
    ranges.push(new vscode.Range(start, end));
  }
  return ranges;
}

async function hythonDocuments(current) {
  const documents = new Map([[current.uri.toString(), current]]);
  const files = await vscode.workspace.findFiles(
    "**/*.hy",
    "**/{.git,node_modules,build,dist,release}/**",
    2000
  );
  for (const uri of files) {
    if (!documents.has(uri.toString())) {
      documents.set(uri.toString(), await vscode.workspace.openTextDocument(uri));
    }
  }
  return [...documents.values()];
}

function isDefinitionLine(line, identifier) {
  const name = escapedRegExp(identifier);
  return new RegExp(
    `^\\s*(?:(?:어싱크\\s+)?(?:데프|클래스)\\s+${name}(?![\\w가-힣])`
    + `|${name}(?![\\w가-힣])\\s*(?::[^=]+)?=(?!=))`
  ).test(line);
}

async function definitionLocations(document, identifier) {
  const result = [];
  for (const candidate of await hythonDocuments(document)) {
    for (const range of identifierRanges(candidate, identifier)) {
      if (isDefinitionLine(candidate.lineAt(range.start.line).text, identifier)) {
        result.push(new vscode.Location(candidate.uri, range));
      }
    }
  }
  return result;
}

async function referenceLocations(document, identifier) {
  const result = [];
  for (const candidate of await hythonDocuments(document)) {
    for (const range of identifierRanges(candidate, identifier)) {
      result.push(new vscode.Location(candidate.uri, range));
    }
  }
  return result;
}

async function provideHover(document, position, token) {
  const word = wordAt(document, position);
  if (!word || token.isCancellationRequested) {
    return undefined;
  }
  try {
    const analysis = await analyze(document, word.range.end, token);
    const completion = analysis?.completions?.items?.find(
      item => item.label === word.text
    );
    const symbol = analysis?.symbols?.find(item => item.name === word.text);
    if (!completion && !symbol) {
      const definitions = await definitionLocations(document, word.text);
      if (!definitions.length) {
        return undefined;
      }
    }
    const markdown = new vscode.MarkdownString();
    markdown.appendCodeblock(word.text, "hython");
    if (symbol) {
      markdown.appendMarkdown(`**${symbol.kind}** · ${symbol.line}줄\n\n`);
    } else if (completion) {
      markdown.appendMarkdown(`**Hython ${completion.kind}**\n\n`);
    } else {
      markdown.appendMarkdown("**Hython 식별자**\n\n");
    }
    markdown.appendMarkdown("Hython 엔진 분석 결과");
    return new vscode.Hover(markdown, word.range);
  } catch (error) {
    output.appendLine(`[호버 실패] ${error.message}`);
    return undefined;
  }
}

async function activeHythonDocument() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== LANGUAGE) {
    vscode.window.showWarningMessage("Hython(.hy) 파일을 먼저 여세요.");
    return undefined;
  }
  if (editor.document.isUntitled) {
    vscode.window.showWarningMessage("파일을 저장한 뒤 실행하세요.");
    return undefined;
  }
  if (configuration().get("run.saveBeforeRun", true)) {
    await editor.document.save();
  }
  return editor.document;
}

function terminalFor(document) {
  const terminal = vscode.window.terminals.find(item => item.name === "Hython")
    || vscode.window.createTerminal({
      name: "Hython",
      cwd: workspaceDirectory(document),
      iconPath: new vscode.ThemeIcon("terminal")
    });
  terminal.show();
  return terminal;
}

async function executeTask(document, engine, taskName, args) {
  const folder = vscode.workspace.getWorkspaceFolder(document.uri);
  const execution = new vscode.ShellExecution(engine, args);
  const task = new vscode.Task(
    {type: "hython", task: taskName},
    folder || vscode.TaskScope.Workspace,
    taskName,
    "Hython",
    execution,
    []
  );
  task.presentationOptions = {
    reveal: vscode.TaskRevealKind.Always,
    panel: vscode.TaskPanelKind.Shared,
    clear: false,
    showReuseMessage: false
  };
  return vscode.tasks.executeTask(task);
}

async function sendCommand(action) {
  const document = await activeHythonDocument();
  if (!document) {
    return;
  }
  const engine = await findEngine(document);
  if (!engine) {
    const choice = await vscode.window.showErrorMessage(
      "Hython 엔진을 찾을 수 없습니다.",
      "경로 선택"
    );
    if (choice === "경로 선택") {
      await selectEngine();
    }
    return;
  }
  const file = document.uri.fsPath;
  if (action === "run") {
    await executeTask(document, engine, "현재 파일 실행", ["run", file]);
  } else if (action === "compile") {
    await executeTask(document, engine, "HBC 컴파일", ["compile", file]);
  } else {
    const hbc = document.uri.fsPath.replace(/\.hy$/i, ".hbc");
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Hython HBC를 준비하는 중…",
        cancellable: false
      },
      async () => {
        const result = await spawn(
          engine,
          ["compile", file],
          {cwd: workspaceDirectory(document)}
        );
        output.append(result.stdout);
        output.append(result.stderr);
        if (result.code !== 0) {
          throw new Error((result.stderr || result.stdout).trim());
        }
      }
    );
    await executeTask(document, engine, "EXE 빌드", ["exe", hbc]);
  }
}

async function selectEngine() {
  const selected = await vscode.window.showOpenDialog({
    canSelectFiles: true,
    canSelectFolders: false,
    canSelectMany: false,
    filters: process.platform === "win32"
      ? {"Hython 실행 파일": ["exe"], "모든 파일": ["*"]}
      : undefined,
    title: "Hython 실행 파일 선택"
  });
  if (!selected?.length) {
    return;
  }
  await configuration().update(
    "executablePath",
    selected[0].fsPath,
    vscode.ConfigurationTarget.Global
  );
  cachedEngine = undefined;
  const document = vscode.window.activeTextEditor?.document;
  const engine = await findEngine(document, true);
  if (engine) {
    vscode.window.showInformationMessage(`Hython 엔진 연결 완료: ${engine}`);
    if (document?.languageId === LANGUAGE) {
      refreshDiagnostics(document);
    }
  } else {
    vscode.window.showErrorMessage("선택한 파일은 Hython 엔진이 아닙니다.");
  }
}

async function debugCurrentFile() {
  const document = await activeHythonDocument();
  if (!document) {
    return;
  }
  const folder = vscode.workspace.getWorkspaceFolder(document.uri);
  await vscode.debug.startDebugging(folder, {
    type: "hython",
    request: "launch",
    name: "현재 Hython 파일 디버그",
    program: document.uri.fsPath
  });
}

async function runEngineUtility(args, title) {
  const document = vscode.window.activeTextEditor?.document;
  const engine = await findEngine(document);
  if (!engine) {
    vscode.window.showErrorMessage("Hython 엔진을 찾을 수 없습니다.");
    return;
  }
  const folder = document
    ? vscode.workspace.getWorkspaceFolder(document.uri)
    : vscode.workspace.workspaceFolders?.[0];
  const execution = new vscode.ShellExecution(engine, args);
  const task = new vscode.Task(
    {type: "hython", task: title},
    folder || vscode.TaskScope.Workspace,
    title,
    "Hython",
    execution
  );
  task.presentationOptions = {
    reveal: vscode.TaskRevealKind.Always,
    panel: vscode.TaskPanelKind.Shared,
    clear: false
  };
  await vscode.tasks.executeTask(task);
}

async function installPackage() {
  const spec = await vscode.window.showInputBox({
    title: "Hython 패키지 설치",
    prompt: "설치할 PyPI 패키지 이름이나 버전 지정자를 입력하세요.",
    placeHolder: "requests 또는 requests==2.32.0",
    validateInput(value) {
      return value.trim() ? undefined : "패키지 이름을 입력하세요.";
    }
  });
  if (spec) {
    await runEngineUtility(["package", "install", spec.trim()], "패키지 설치");
  }
}

async function createProject() {
  const selected = await vscode.window.showOpenDialog({
    title: "새 Hython 프로젝트 폴더 선택",
    canSelectFiles: false,
    canSelectFolders: true,
    canSelectMany: false,
    openLabel: "이 폴더에 만들기"
  });
  if (!selected?.length) {
    return;
  }
  const root = selected[0];
  const main = vscode.Uri.joinPath(root, "main.hy");
  const vscodeFolder = vscode.Uri.joinPath(root, ".vscode");
  const launch = vscode.Uri.joinPath(vscodeFolder, "launch.json");
  const tasks = vscode.Uri.joinPath(vscodeFolder, "tasks.json");
  if (fs.existsSync(main.fsPath)) {
    const answer = await vscode.window.showWarningMessage(
      "main.hy가 이미 있습니다. 기존 파일을 유지하고 프로젝트 설정만 만듭니다.",
      "계속",
      "취소"
    );
    if (answer !== "계속") {
      return;
    }
  } else {
    await vscode.workspace.fs.writeFile(
      main,
      Buffer.from(
        "데프 메인():\n    프린트(\"안녕하세요, Hython!\")\n\n"
        + "이프 __네임__ == \"__메인__\":\n    메인()\n",
        "utf8"
      )
    );
  }
  await vscode.workspace.fs.createDirectory(vscodeFolder);
  if (!fs.existsSync(launch.fsPath)) {
    await vscode.workspace.fs.writeFile(
      launch,
      Buffer.from(JSON.stringify({
        version: "0.2.0",
        configurations: [{
          type: "hython",
          request: "launch",
          name: "Hython: main.hy",
          program: "${workspaceFolder}/main.hy"
        }]
      }, null, 2), "utf8")
    );
  }
  if (!fs.existsSync(tasks.fsPath)) {
    await vscode.workspace.fs.writeFile(
      tasks,
      Buffer.from(JSON.stringify({
        version: "2.0.0",
        tasks: [
          {
            label: "Hython: 실행",
            type: "shell",
            command: "hython",
            args: ["run", "${workspaceFolder}/main.hy"],
            group: "test"
          },
          {
            label: "Hython: HBC 컴파일",
            type: "shell",
            command: "hython",
            args: ["compile", "${workspaceFolder}/main.hy"],
            group: "build",
            problemMatcher: []
          }
        ]
      }, null, 2), "utf8")
    );
  }
  const open = await vscode.window.showInformationMessage(
    "Hython 프로젝트를 만들었습니다.",
    "프로젝트 열기"
  );
  if (open === "프로젝트 열기") {
    await vscode.commands.executeCommand("vscode.openFolder", root);
  } else {
    await vscode.window.showTextDocument(await vscode.workspace.openTextDocument(main));
  }
}

function activate(context) {
  status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 30);
  status.command = "hython.selectEngine";
  status.text = "$(sync~spin) Hython 확인";
  status.show();

  context.subscriptions.push(
    diagnostics,
    output,
    status,
    vscode.commands.registerCommand("hython.runFile", () => sendCommand("run")),
    vscode.commands.registerCommand("hython.compileFile", () => sendCommand("compile")),
    vscode.commands.registerCommand("hython.buildExe", () => sendCommand("exe")),
    vscode.commands.registerCommand("hython.debugFile", debugCurrentFile),
    vscode.commands.registerCommand("hython.selectEngine", selectEngine),
    vscode.commands.registerCommand("hython.newProject", createProject),
    vscode.commands.registerCommand("hython.installPackage", installPackage),
    vscode.commands.registerCommand(
      "hython.updateEngine",
      () => runEngineUtility(["update"], "엔진과 문법 업데이트")
    ),
    vscode.commands.registerCommand("hython.analyzeFile", () => {
      const document = vscode.window.activeTextEditor?.document;
      if (document) {
        refreshDiagnostics(document);
      }
    }),
    vscode.commands.registerCommand("hython.openTerminal", async () => {
      const document = vscode.window.activeTextEditor?.document;
      if (document) {
        terminalFor(document);
      }
    }),
    vscode.workspace.onDidOpenTextDocument(refreshDiagnostics),
    vscode.workspace.onDidSaveTextDocument(refreshDiagnostics),
    vscode.workspace.onDidChangeTextDocument(event => scheduleDiagnostics(event.document)),
    vscode.workspace.onDidCloseTextDocument(document => {
      diagnostics.delete(document.uri);
      const key = document.uri.toString();
      clearTimeout(timers.get(key));
      timers.delete(key);
    }),
    vscode.workspace.onDidChangeConfiguration(event => {
      if (event.affectsConfiguration("hython")) {
        cachedEngine = undefined;
        findEngine(vscode.window.activeTextEditor?.document, true);
      }
    }),
    vscode.languages.registerCompletionItemProvider(
      LANGUAGE,
      {
        async provideCompletionItems(document, position, token) {
          try {
            const result = await analyze(document, position, token);
            return (result?.completions?.items || []).map(item => {
              const completion = new vscode.CompletionItem(
                item.label,
                completionKind(item.kind)
              );
              completion.insertText = item.insertText || item.label;
              completion.detail = `Hython ${item.kind}`;
              return completion;
            });
          } catch (error) {
            output.appendLine(`[자동완성 실패] ${error.message}`);
            return [];
          }
        }
      },
      ..."_가나다라마바사아자차카타파하abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ".split("")
    ),
    vscode.languages.registerDocumentSymbolProvider(LANGUAGE, {
      async provideDocumentSymbols(document, token) {
        try {
          const result = await analyze(document, undefined, token);
          return (result?.symbols || []).map(item => {
            const line = Math.max(0, (item.line || 1) - 1);
            const column = Math.max(0, item.column || 0);
            const range = document.lineAt(line).range;
            return new vscode.DocumentSymbol(
              item.name,
              item.kind,
              symbolKind(item.kind),
              range,
              new vscode.Range(line, column, line, Math.max(column + 1, range.end.character))
            );
          });
        } catch (error) {
          output.appendLine(`[심볼 분석 실패] ${error.message}`);
          return [];
        }
      }
    }),
    vscode.languages.registerHoverProvider(LANGUAGE, {
      provideHover
    }),
    vscode.languages.registerDefinitionProvider(LANGUAGE, {
      async provideDefinition(document, position) {
        const word = wordAt(document, position);
        return word ? definitionLocations(document, word.text) : [];
      }
    }),
    vscode.languages.registerReferenceProvider(LANGUAGE, {
      async provideReferences(document, position, context, token) {
        const word = wordAt(document, position);
        if (!word || token.isCancellationRequested) {
          return [];
        }
        const locations = await referenceLocations(document, word.text);
        if (context.includeDeclaration) {
          return locations;
        }
        const definitions = new Set(
          (await definitionLocations(document, word.text)).map(
            item => `${item.uri}:${item.range.start.line}:${item.range.start.character}`
          )
        );
        return locations.filter(item => !definitions.has(
          `${item.uri}:${item.range.start.line}:${item.range.start.character}`
        ));
      }
    }),
    vscode.languages.registerDocumentHighlightProvider(LANGUAGE, {
      provideDocumentHighlights(document, position) {
        const word = wordAt(document, position);
        if (!word) {
          return [];
        }
        return identifierRanges(document, word.text).map(range =>
          new vscode.DocumentHighlight(range, vscode.DocumentHighlightKind.Read)
        );
      }
    }),
    vscode.languages.registerRenameProvider(LANGUAGE, {
      prepareRename(document, position) {
        const word = wordAt(document, position);
        if (!word) {
          throw new Error("이름을 변경할 Hython 식별자가 아닙니다.");
        }
        if (RESERVED_WORDS.has(word.text)) {
          throw new Error("Hython 예약어의 이름은 변경할 수 없습니다.");
        }
        return {range: word.range, placeholder: word.text};
      },
      async provideRenameEdits(document, position, newName, token) {
        const word = wordAt(document, position);
        if (
          !word
          || token.isCancellationRequested
          || !/^[A-Za-z_가-힣][\w가-힣]*$/u.test(newName)
        ) {
          return undefined;
        }
        const edit = new vscode.WorkspaceEdit();
        for (const location of await referenceLocations(document, word.text)) {
          edit.replace(location.uri, location.range, newName);
        }
        return edit;
      }
    }),
    vscode.languages.registerCodeLensProvider(LANGUAGE, {
      provideCodeLenses(document) {
        if (!configuration().get("codeLens.enabled", true) || !document.lineCount) {
          return [];
        }
        const range = document.lineAt(0).range;
        return [
          new vscode.CodeLens(range, {
            command: "hython.runFile",
            title: "$(play) 현재 파일 실행"
          }),
          new vscode.CodeLens(range, {
            command: "hython.debugFile",
            title: "$(debug-alt) 디버그"
          }),
          new vscode.CodeLens(range, {
            command: "hython.compileFile",
            title: "$(package) HBC 컴파일"
          })
        ];
      }
    }),
    vscode.debug.registerDebugConfigurationProvider("hython", {
      provideDebugConfigurations() {
        return [{
          type: "hython",
          request: "launch",
          name: "현재 Hython 파일",
          program: "${file}"
        }];
      },
      resolveDebugConfiguration(folder, config) {
        if (!config.type) {
          config.type = "hython";
        }
        if (!config.request) {
          config.request = "launch";
        }
        if (!config.name) {
          config.name = "현재 Hython 파일";
        }
        if (!config.program) {
          const editor = vscode.window.activeTextEditor;
          if (editor?.document.languageId === LANGUAGE) {
            config.program = editor.document.uri.fsPath;
          }
        }
        if (!config.program) {
          vscode.window.showErrorMessage("디버깅할 Hython 파일을 여세요.");
          return undefined;
        }
        return config;
      }
    }),
    vscode.debug.registerDebugAdapterDescriptorFactory("hython", {
      createDebugAdapterDescriptor() {
        return new vscode.DebugAdapterInlineImplementation(
          new HythonDebugAdapter(findEngine, output)
        );
      }
    })
  );

  for (const document of vscode.workspace.textDocuments) {
    if (document.languageId === LANGUAGE) {
      refreshDiagnostics(document);
    }
  }
  findEngine(vscode.window.activeTextEditor?.document);
}

function deactivate() {
  for (const timer of timers.values()) {
    clearTimeout(timer);
  }
  timers.clear();
}

module.exports = {activate, deactivate};
