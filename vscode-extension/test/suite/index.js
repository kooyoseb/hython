"use strict";

const {runTests} = require("./extension.test");

async function run() {
  await runTests();
}

module.exports = {run};
