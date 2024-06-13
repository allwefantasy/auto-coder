/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ([
/* 0 */
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {


var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
    __setModuleDefault(result, mod);
    return result;
};
Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.deactivate = exports.activate = void 0;
// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = __importStar(__webpack_require__(1));
// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
function activate(context) {
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    // This line of code will only be executed once when your extension is activated
    console.log('Congratulations, your extension "auto-coder" is now active!');
    // The command has been defined in the package.json file
    // Now provide the implementation of the command with registerCommand
    // The commandId parameter must match the command field in package.json
    let disposable = vscode.commands.registerCommand('auto-coder.runInTerminal', (uri) => {
        const filePath = uri.fsPath;
        const workspaceFolders = vscode.workspace.workspaceFolders;
        let projectRoot;
        if (workspaceFolders) {
            projectRoot = workspaceFolders[0].uri.fsPath;
        }
        const terminals = vscode.window.terminals;
        let terminal;
        if (terminals.length === 0) {
            terminal = vscode.window.createTerminal();
        }
        else {
            terminal = terminals[0];
        }
        terminal.show();
        if (projectRoot) {
            terminal.sendText(`cd ${projectRoot}`);
        }
        terminal.sendText(`auto-coder --file ${filePath}`);
    });
    context.subscriptions.push(disposable);
    let createRequirementDisposable = vscode.commands.registerCommand('auto-coder.createRequirement', async (uri) => {
        const requirement = await vscode.window.showInputBox({
            placeHolder: '请输入需求',
            prompt: '需求'
        });
        const model = await vscode.window.showInputBox({
            placeHolder: '请输入模型名',
            prompt: '模型名'
        });
        const embModel = await vscode.window.showInputBox({
            placeHolder: '请输入向量模型名',
            prompt: '向量模型名'
        });
        if (requirement && model && embModel) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            let projectRoot;
            if (workspaceFolders) {
                projectRoot = workspaceFolders[0].uri.fsPath;
            }
            const terminals = vscode.window.terminals;
            let terminal;
            if (terminals.length === 0) {
                terminal = vscode.window.createTerminal();
            }
            else {
                terminal = terminals[0];
            }
            terminal.show();
            if (projectRoot) {
                terminal.sendText(`cd ${projectRoot}`);
            }
            terminal.sendText(`auto-coder agent planner --model ${model} --emb_model ${embModel} --query "${requirement}"`);
        }
    });
    context.subscriptions.push(createRequirementDisposable);
}
exports.activate = activate;
// This method is called when your extension is deactivated
function deactivate() { }
exports.deactivate = deactivate;


/***/ }),
/* 1 */
/***/ ((module) => {

module.exports = require("vscode");

/***/ })
/******/ 	]);
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module is referenced by other modules so it can't be inlined
/******/ 	var __webpack_exports__ = __webpack_require__(0);
/******/ 	module.exports = __webpack_exports__;
/******/ 	
/******/ })()
;
//# sourceMappingURL=extension.js.map