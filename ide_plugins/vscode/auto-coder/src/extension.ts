// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import path = require('path');
import fs = require('fs');
import yaml = require('js-yaml');

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
		const workspaceFolders = vscode.workspace.workspaceFolders;
		if (!workspaceFolders) {
			vscode.window.showErrorMessage('请先打开一个工作区');
			return;
		}
		const projectRoot = workspaceFolders[0].uri.fsPath;
		const autoCorderDir = path.join(projectRoot, '.auto-coder');
		if (!fs.existsSync(autoCorderDir)) {
			const action = await vscode.window.showErrorMessage(
				'当前工作区尚未初始化auto-coder项目,是否立即初始化?',
				'立即初始化'
			);
			if (action === '立即初始化') {
				vscode.commands.executeCommand('auto-coder.initProject');
			}
			return;
		}
        
		const baseConfigFile = path.join(projectRoot, 'actions', 'base', 'base.yml');
		let model, embModel;
		
		if (fs.existsSync(baseConfigFile)) {			
			const baseConfig = yaml.load(fs.readFileSync(baseConfigFile, 'utf8')) as Record<string, unknown>;
			model = baseConfig?.model as string;
			embModel = baseConfig?.emb_model as string;
		}

		const requirement = await vscode.window.showInputBox({
			placeHolder: '请输入需求',
			prompt: '需求'
		});

		if (!requirement) {
			return;
		}
        
		if (!model) {
			model = await vscode.window.showInputBox({
				placeHolder: '请输入模型名',
				prompt: '模型名'
			});
		}

		if (!embModel) {
			embModel = await vscode.window.showInputBox({
				placeHolder: '请输入向量模型名',
				prompt: '向量模型名'
			});
		}	

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