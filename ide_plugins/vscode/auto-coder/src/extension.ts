// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import path = require('path');
import fs = require('fs');

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {

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
		} else {
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
			} else {
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

	let initProjectDisposable = vscode.commands.registerCommand('auto-coder.initProject', async (uri) => {
		const workspaceFolders = vscode.workspace.workspaceFolders;
		let projectRoot;
		if (workspaceFolders) {
			projectRoot = workspaceFolders[0].uri.fsPath;
		}

		const terminals = vscode.window.terminals;
		let terminal;

		if (terminals.length === 0) {
			terminal = vscode.window.createTerminal();
		} else {
			terminal = terminals[0];
		}

		terminal.show();
		if (projectRoot) {
			terminal.sendText(`cd ${projectRoot}`);
		}
		terminal.sendText('auto-coder init --source_dir .');
	});

	context.subscriptions.push(initProjectDisposable);	
}


export function deactivate() { }
