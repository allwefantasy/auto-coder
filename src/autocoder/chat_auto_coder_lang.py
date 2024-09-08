import locale

MESSAGES = {
    "en": {
        "initializing": "🚀 Initializing system...",
        "not_initialized": "The current directory is not initialized as an auto-coder project.",
        "init_prompt": "Do you want to initialize the project now? (y/n): ",
        "init_success": "Project initialized successfully.",
        "init_fail": "Failed to initialize the project.",
        "init_manual": "Please try manually: auto-coder init --source_dir .",
        "exit_no_init": "Exiting without initialization.",
        "created_dir": "Created directory: {}",
        "init_complete": "Project initialization completed.",
        "checking_ray": "Checking Ray status...",
        "ray_not_running": "Ray is not running. Starting Ray...",
        "ray_start_success": "Ray started successfully.",
        "ray_start_fail": "Failed to start Ray. Please start it manually.",
        "ray_running": "Ray is already running.",
        "checking_model": "Checking deepseek_chat model availability...",
        "model_available": "deepseek_chat model is available.",
        "model_timeout": "Command timed out. deepseek_chat model might not be available.",
        "model_error": "Error occurred while checking deepseek_chat model.",
        "model_not_available": "deepseek_chat model is not available. Please choose a provider:",
        "provider_selection": "Select a provider for deepseek_chat model:",
        "no_provider": "No provider selected. Exiting initialization.",
        "enter_api_key": "Please enter your API key: ",
        "deploying_model": "Deploying deepseek_chat model using {}...",
        "deploy_complete": "Deployment completed.",
        "deploy_fail": "Deployment failed. Please try again or deploy manually.",
        "validating_deploy": "Validating the deployment...",
        "validation_success": "Validation successful. deepseek_chat model is now available.",
        "validation_fail": "Validation failed. The model might not be deployed correctly.",
        "manual_start": "Please try to start the model manually using:",
        "init_complete_final": "Initialization completed.",
    },
    "zh": {
        "initializing": "🚀 正在初始化系统...",
        "not_initialized": "当前目录未初始化为auto-coder项目。",
        "init_prompt": "是否现在初始化项目？(y/n): ",
        "init_success": "项目初始化成功。",
        "init_fail": "项目初始化失败。",
        "init_manual": "请尝试手动初始化：auto-coder init --source_dir .",
        "exit_no_init": "退出而不初始化。",
        "created_dir": "创建目录：{}",
        "init_complete": "项目初始化完成。",
        "checking_ray": "正在检查Ray状态...",
        "ray_not_running": "Ray未运行。正在启动Ray...",
        "ray_start_success": "Ray启动成功。",
        "ray_start_fail": "Ray启动失败。请手动启动。",
        "ray_running": "Ray已经在运行。",
        "checking_model": "正在检查deepseek_chat模型可用性...",
        "model_available": "deepseek_chat模型可用。",
        "model_timeout": "命令超时。deepseek_chat模型可能不可用。",
        "model_error": "检查deepseek_chat模型时出错。",
        "model_not_available": "deepseek_chat模型不可用。请选择一个提供商：",
        "provider_selection": "为deepseek_chat模型选择一个提供商：",
        "no_provider": "未选择提供商。退出初始化。",
        "enter_api_key": "请输入您的API密钥：",
        "deploying_model": "正在使用{}部署deepseek_chat模型...",
        "deploy_complete": "部署完成。",
        "deploy_fail": "部署失败。请重试或手动部署。",
        "validating_deploy": "正在验证部署...",
        "validation_success": "验证成功。deepseek_chat模型现在可用。",
        "validation_fail": "验证失败。模型可能未正确部署。",
        "manual_start": "请尝试使用以下命令手动启动模型：",
        "init_complete_final": "初始化完成。",
    }
}

def get_system_language():
    try:
        return locale.getdefaultlocale()[0][:2]
    except:
        return 'en'

def get_message(key):
    lang = get_system_language()
    return MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'][key])