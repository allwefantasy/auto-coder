import locale

MESSAGES = {
    "en": {
        "initializing": "🚀 Initializing system...",        
    },
    "zh": {
        "initializing": "🚀 正在初始化系统...",        
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
