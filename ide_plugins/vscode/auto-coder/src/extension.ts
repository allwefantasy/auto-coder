import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as os from 'os';
import * as child_process from 'child_process';
import * as net from 'net';

let autoCoderServerPort: number | undefined;
let autoCoderIdPath: string | undefined;

async function selectPythonEnvironment(): Promise<string | undefined> {
    if (autoCoderIdPath && fs.existsSync(autoCoderIdPath)) {
        return autoCoderIdPath;
    }

    const condaEnvironments = await getCondaEnvironments();
    const quickPickItems = condaEnvironments.map(env => ({
        label: env.name,
        description: env.path
    }));

    const selectedItem = await vscode.window.showQuickPick(quickPickItems, {
        placeHolder: 'Select a Python environment for auto-coder'
    });

    if (selectedItem) {
        autoCoderIdPath = selectedItem.description;
        // 保存选择的路径到 VSCode 配置
        await vscode.workspace.getConfiguration().update('autoCoder.pythonEnvironmentPath', autoCoderIdPath, vscode.ConfigurationTarget.Global);
        return autoCoderIdPath;
    }

    return undefined;
}

async function getCondaEnvironments(): Promise<{ name: string, path: string }[]> {
    return new Promise((resolve, reject) => {
        child_process.exec('conda env list --json', (error, stdout) => {
            if (error) {
                reject(error);
                return;
            }
            const envList = JSON.parse(stdout);
            const environments = envList.envs.map((envPath: string) => ({
                name: path.basename(envPath),
                path: envPath
            }));
            resolve(environments);
        });
    });
}

function getOrCreateAutoCoderTerminal(): vscode.Terminal {
	const existingTerminal = vscode.window.terminals.find(t => t.name === 'auto-coder-vscode');
	if (existingTerminal) {
		return existingTerminal;
	} else {
		const newTerminal = vscode.window.createTerminal('auto-coder-vscode');
		newTerminal.sendText('conda activate auto-coder');
		return newTerminal;
	}
}

function findAvailablePort(startPort: number): Promise<number> {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.listen(startPort, () => {
            const port = (server.address() as net.AddressInfo).port;
            server.close(() => resolve(port));
        });
        server.on('error', () => {
            findAvailablePort(startPort + 1).then(resolve, reject);
        });
    });
}

async function startAutoCoderServer(context: vscode.ExtensionContext) {
    const selectedPythonPath = await selectPythonEnvironment();	

    if (!selectedPythonPath) {
        vscode.window.showErrorMessage('No Python environment selected. Auto-coder server cannot start.');
        return;
    }

    const port = await findAvailablePort(8081);
    autoCoderServerPort = port; // 保存端口到全局变量

    let autoCoderId: string;
    if (os.platform() === 'win32') {
        autoCoderId = path.join(selectedPythonPath, 'Scripts', 'auto-coder-serve.exe');
    } else {
        autoCoderId = path.join(selectedPythonPath, 'bin', 'auto-coder-serve');
    }

    const serverProcess = child_process.spawn(autoCoderId, ['--host', '127.0.0.1', '--port', port.toString()], {
        cwd: vscode.workspace.workspaceFolders ? vscode.workspace.workspaceFolders[0].uri.fsPath : undefined
    });

    serverProcess.stdout.on('data', (data) => {
        console.log(`auto-coder server stdout: ${data}`);
    });

    serverProcess.stderr.on('data', (data) => {
        console.error(`auto-coder server stderr: ${data}`);
    });

    serverProcess.on('error', (error) => {
        console.error(`Failed to start auto-coder server: ${error}`);
        vscode.window.showErrorMessage(`Failed to start auto-coder server. Please make sure auto-coder is installed and activated in your environment.`);
        autoCoderServerPort = undefined;
    });

    serverProcess.on('close', (code) => {
        console.log(`auto-coder server process exited with code ${code}`);
        autoCoderServerPort = undefined; // 清除端口
    });

    context.subscriptions.push({
        dispose: () => {
            serverProcess.kill();
            autoCoderServerPort = undefined; // 清除端口
        }
    });

    vscode.window.showInformationMessage(`Auto-coder server started on port ${port}`);
}

export function activate(context: vscode.ExtensionContext) {
	const outputChannel = vscode.window.createOutputChannel('auto-coder-copilot-extension');
	outputChannel.appendLine('Congratulations, your extension "auto-coder" is now active!');

    // 从 VSCode 配置中读取保存的 Python 环境路径
    autoCoderIdPath = vscode.workspace.getConfiguration().get('autoCoder.pythonEnvironmentPath');

    startAutoCoderServer(context);

function updateActiveEditorFile() {
	const activeEditor = vscode.window.activeTextEditor;
	const docs = vscode.workspace.textDocuments

	if (activeEditor && activeEditor.document.uri.scheme === 'file') {
		const activeFilePath = activeEditor.document.uri.fsPath;
		const workspaceFolder = vscode.workspace.getWorkspaceFolder(activeEditor.document.uri);

		if (workspaceFolder) {
			const autoCoderId = path.join(workspaceFolder.uri.fsPath, '.auto-coder');			

			if (fs.existsSync(autoCoderId)) {
				const idePath = path.join(autoCoderId, 'ide');
                if (!fs.existsSync(idePath)) {
					fs.mkdirSync(idePath);
				}
				const activeEditorFile = path.join(idePath, 'active_editor.json');
				const content = {
					activeFile: { path: activeFilePath },
					files: docs
						.filter(doc => doc.uri.scheme === 'file' && doc.uri.fsPath !== activeFilePath)
						.map(doc => ({ path: doc.uri.fsPath }))
				};
				fs.writeFileSync(activeEditorFile, JSON.stringify(content, null, 2));				
			}
		}
	}
}

	// Register event listeners for editor changes
	vscode.window.onDidChangeActiveTextEditor(() => {
		updateActiveEditorFile();
	});

	vscode.workspace.onDidOpenTextDocument(() => {
		updateActiveEditorFile();
	});

	vscode.workspace.onDidCloseTextDocument(() => {
		updateActiveEditorFile();
	});

	// Update for the initial state
	updateActiveEditorFile();

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

		const terminal = getOrCreateAutoCoderTerminal();
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
			model = baseConfig?.planner_model as string || baseConfig?.model as string;
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

			const terminal = getOrCreateAutoCoderTerminal();

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

		const terminal = getOrCreateAutoCoderTerminal();

		terminal.show();
		if (projectRoot) {
			terminal.sendText(`cd ${projectRoot}`);
		}
		terminal.sendText('auto-coder init --source_dir .');
	});

	context.subscriptions.push(initProjectDisposable);

	let createYamlDisposable = vscode.commands.registerCommand('auto-coder.createYaml', async (uri) => {
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

		const panel = vscode.window.createWebviewPanel(
			'createYamlForm',
			'Create YAML File',
			vscode.ViewColumn.One,
			{
				enableScripts: true
			}
		);

		const scriptPathOnDisk = vscode.Uri.file(path.join(context.extensionPath, 'dist', 'web.js'));
		const scriptUri = panel.webview.asWebviewUri(scriptPathOnDisk);
		const colorTheme = vscode.window.activeColorTheme;

		panel.webview.html = getWebviewContent(scriptUri, colorTheme);


		const terminal = getOrCreateAutoCoderTerminal();

		terminal.show();
		if (projectRoot) {
			terminal.sendText(`cd ${projectRoot}`);
		}

		// Handle messages from the webview
		panel.webview.onDidReceiveMessage(
			message => {
				switch (message.type) {
					case 'submitForm':
						handleSubmitForm(message.value, panel, workspaceFolders[0].uri.fsPath);
						return;
					case 'selectPath':
						vscode.window.showOpenDialog({
							canSelectFiles: true,
							canSelectFolders: true,
							canSelectMany: false,
							openLabel: 'Select'
						}).then(fileUri => {
							if (fileUri && fileUri[0]) {
								panel.webview.postMessage({ type: 'selectedPath', value: fileUri[0].fsPath });
							}
						});
						return;
				}
			},
			undefined,
			context.subscriptions
		);

		function handleSubmitForm(formData: any, panel: vscode.WebviewPanel, projectRoot: string) {
			const actionsDir = path.join(projectRoot, 'actions');
			fs.readdir(actionsDir, (err, files) => {
				if (err) {
					panel.webview.postMessage({ type: 'submitFormResponse', success: false, error: 'Failed to read actions directory' });
					return;
				}

				let maxNumber = 0;
				files.forEach(file => {
					const parts = file.split('_');
					if (parts.length > 1) {
						const num = parseInt(parts[0]);
						if (!isNaN(num) && num > maxNumber) {
							maxNumber = num;
						}
					}
				});

				const newNumber = maxNumber + 1;
				const newFileName = `${newNumber.toString().padStart(3, '0')}_plugin_action.yml`;
				const newFilePath = path.join(actionsDir, newFileName);

				const yamlContent = yaml.dump(formData);

				fs.writeFile(newFilePath, yamlContent, (err) => {
					if (err) {
						panel.webview.postMessage({ type: 'submitFormResponse', success: false, error: 'Failed to write YAML file' });
					} else {
						// Open the newly created file in VSCode
						vscode.workspace.openTextDocument(newFilePath).then(doc => {
							vscode.window.showTextDocument(doc);
						});
						panel.webview.postMessage({ type: 'submitFormResponse', success: true });
						panel.dispose();
					}
				});
			});
		}
	});

	context.subscriptions.push(createYamlDisposable);

	let chatDisposable = vscode.commands.registerCommand('auto-coder.chat', () => {
		const panel = vscode.window.createWebviewPanel(
			'chatView',
			'Auto Coder Chat',
			vscode.ViewColumn.One,
			{
				enableScripts: true
			}
		);

		const scriptPathOnDisk = vscode.Uri.file(path.join(context.extensionPath, 'dist', 'web.js'));
		const scriptUri = panel.webview.asWebviewUri(scriptPathOnDisk);
		const colorTheme = vscode.window.activeColorTheme;

		panel.webview.html = getWebviewContent(scriptUri, colorTheme, 'chat');

		// Handle messages from the webview
		panel.webview.onDidReceiveMessage(
			message => {
				switch (message.type) {
					case 'getAutoCoderServerPort':
						if (autoCoderServerPort) {
							panel.webview.postMessage({ type: 'autoCoderServerPort', port: autoCoderServerPort });
						}
						return;
				}
			},
			undefined,
			context.subscriptions
		);
	});

	context.subscriptions.push(chatDisposable);
}

function getWebviewContent(scriptUri: vscode.Uri, colorTheme: vscode.ColorTheme,view:string="create_yaml") {
	const isDark = colorTheme.kind === vscode.ColorThemeKind.Dark
	return `
	  <!DOCTYPE html>
	  <html lang="en">
	  <head>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<title></title>
	  </head>
	  <body>
		<div id="root"></div>
		<script>
		  window.vscodeColorTheme = ${isDark};
		  window.view = "${view}";
		</script>
		<script src="${scriptUri}"></script>
	  </body>
	  </html>
	`;
}


export function deactivate() { }
