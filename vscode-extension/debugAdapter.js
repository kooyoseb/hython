"use strict";

const vscode = require("vscode");
const childProcess = require("child_process");
const readline = require("readline");
const path = require("path");

class HythonDebugAdapter {
  constructor(findEngine, output) {
    this.findEngine = findEngine;
    this.output = output;
    this.emitter = new vscode.EventEmitter();
    this.onDidSendMessage = this.emitter.event;
    this.sequence = 1;
    this.breakpoints = [];
    this.variables = {};
    this.currentLine = 1;
    this.currentFunction = "<module>";
    this.program = "";
    this.process = undefined;
    this.terminated = false;
  }

  dispose() {
    this.stopProcess();
    this.emitter.dispose();
  }

  send(message) {
    message.seq = this.sequence++;
    this.emitter.fire(message);
  }

  response(request, body = {}) {
    this.send({
      type: "response",
      request_seq: request.seq,
      success: true,
      command: request.command,
      body
    });
  }

  failure(request, message) {
    this.send({
      type: "response",
      request_seq: request.seq,
      success: false,
      command: request.command,
      message
    });
  }

  event(event, body = {}) {
    this.send({type: "event", event, body});
  }

  write(command, payload = {}) {
    if (!this.process || this.process.killed || !this.process.stdin.writable) {
      return;
    }
    this.process.stdin.write(`${JSON.stringify({command, ...payload})}\n`);
  }

  async launch(request) {
    const program = request.arguments?.program;
    if (!program) {
      this.failure(request, "디버깅할 Hython 파일이 지정되지 않았습니다.");
      return;
    }
    this.program = path.resolve(program);
    try {
      const document = await vscode.workspace.openTextDocument(this.program);
      const engine = await this.findEngine(document);
      if (!engine) {
        this.failure(request, "Hython 엔진을 찾을 수 없습니다.");
        return;
      }
      this.process = childProcess.spawn(
        engine,
        ["ide", "debug", this.program],
        {
          cwd: path.dirname(this.program),
          windowsHide: true,
          shell: false,
          env: {...global.process.env, PYTHONUTF8: "1"}
        }
      );
      this.process.on("error", error => {
        this.event("output", {
          category: "stderr",
          output: `Hython 디버거 시작 실패: ${error.message}\n`
        });
        this.finish(1);
      });
      this.process.stderr.setEncoding("utf8");
      this.process.stderr.on("data", text => this.event("output", {
        category: "stderr",
        output: String(text)
      }));
      readline.createInterface({input: this.process.stdout}).on(
        "line",
        line => this.handleEngineEvent(line)
      );
      this.process.on("close", code => this.finish(code || 0));
      this.response(request);
    } catch (error) {
      this.failure(request, error.message);
    }
  }

  handleEngineEvent(line) {
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      this.event("output", {category: "console", output: `${line}\n`});
      return;
    }
    switch (message.event) {
      case "initialized":
        this.event("initialized");
        break;
      case "breakpoints":
        break;
      case "stopped":
        this.currentLine = Math.max(1, message.line || 1);
        this.currentFunction = message.function || "<module>";
        this.variables = message.variables || {};
        this.event("stopped", {
          reason: message.reason === "breakpoint" ? "breakpoint" : "step",
          description: message.reason === "breakpoint"
            ? "Hython 중단점"
            : "Hython 한 단계 실행",
          threadId: 1,
          allThreadsStopped: true
        });
        break;
      case "output":
        this.event("output", {
          category: message.category || "stdout",
          output: message.text || ""
        });
        break;
      case "error":
        this.event("output", {
          category: "stderr",
          output: `${message.message || "Hython 디버그 오류"}\n`
        });
        break;
      case "exception":
        this.event("output", {
          category: "stderr",
          output: `${message.type || "오류"}: ${message.message || ""}\n`
            + (message.traceback || "")
        });
        break;
      case "terminated":
        this.finish(message.exitCode || 0);
        break;
      default:
        this.output.appendLine(`[디버거] 알 수 없는 이벤트: ${line}`);
    }
  }

  finish(exitCode) {
    if (this.terminated) {
      return;
    }
    this.terminated = true;
    this.event("exited", {exitCode});
    this.event("terminated");
  }

  stopProcess() {
    if (!this.process || this.process.killed) {
      return;
    }
    this.write("stop");
    setTimeout(() => {
      if (this.process && !this.process.killed) {
        this.process.kill();
      }
    }, 800).unref();
  }

  handleMessage(request) {
    if (request.type !== "request") {
      return;
    }
    switch (request.command) {
      case "initialize":
        this.response(request, {
          supportsConfigurationDoneRequest: true,
          supportsEvaluateForHovers: true,
          supportsTerminateRequest: true
        });
        break;
      case "launch":
        this.launch(request);
        break;
      case "setBreakpoints": {
        this.breakpoints = (request.arguments?.breakpoints || [])
          .map(item => item.line)
          .filter(line => Number.isInteger(line) && line > 0);
        this.write("setBreakpoints", {lines: this.breakpoints});
        this.response(request, {
          breakpoints: this.breakpoints.map(line => ({
            verified: true,
            line,
            source: request.arguments?.source
          }))
        });
        break;
      }
      case "setExceptionBreakpoints":
        this.response(request, {breakpoints: []});
        break;
      case "configurationDone":
        this.write("continue");
        this.response(request);
        break;
      case "threads":
        this.response(request, {threads: [{id: 1, name: "Hython 주 스레드"}]});
        break;
      case "stackTrace":
        this.response(request, {
          stackFrames: [{
            id: 1,
            name: this.currentFunction,
            source: {name: path.basename(this.program), path: this.program},
            line: this.currentLine,
            column: 1
          }],
          totalFrames: 1
        });
        break;
      case "scopes":
        this.response(request, {
          scopes: [{
            name: "지역 변수",
            presentationHint: "locals",
            variablesReference: 1,
            expensive: false
          }]
        });
        break;
      case "variables":
        this.response(request, {
          variables: Object.entries(this.variables).map(([name, value]) => ({
            name,
            type: value.type || "",
            value: value.value || "",
            variablesReference: 0
          }))
        });
        break;
      case "evaluate": {
        const value = this.variables[request.arguments?.expression];
        this.response(request, {
          result: value?.value || "정의되지 않은 변수",
          type: value?.type || "",
          variablesReference: 0
        });
        break;
      }
      case "continue":
        this.write("continue");
        this.response(request, {allThreadsContinued: true});
        break;
      case "next":
      case "stepIn":
      case "stepOut":
        this.write("step");
        this.response(request);
        break;
      case "pause":
        this.response(request);
        break;
      case "terminate":
      case "disconnect":
        this.stopProcess();
        this.response(request);
        break;
      default:
        this.response(request);
    }
  }
}

module.exports = {HythonDebugAdapter};
