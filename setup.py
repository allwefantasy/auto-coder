import os
from setuptools import find_packages
from setuptools import setup

folder = os.path.dirname(__file__)
version_path = os.path.join(folder, "src", "autocoder", "version.py")

__version__ = None
with open(version_path) as f:
    exec(f.read(), globals())

req_path = os.path.join(folder, "requirements.txt")
install_requires = []
if os.path.exists(req_path):
    with open(req_path, 'r') as fp:
        install_requires = [line.strip() for line in fp]

readme_path = os.path.join(folder, "README.md")
readme_contents = ""
if os.path.exists(readme_path):
    with open(readme_path, 'r') as fp:
        readme_contents = fp.read().strip()

setup(
    name="auto-coder",
    version=__version__,
    description="AutoCoder: AutoCoder",
    author="allwefantasy",
    long_description=readme_contents,
    long_description_content_type="text/markdown",
    entry_points={
        'console_scripts': [
            'auto-coder = autocoder.auto_coder:main',
            'auto-coder.core = autocoder.auto_coder:main',
            'chat-auto-coder = autocoder.chat_auto_coder:main',
            'auto-coder.chat = autocoder.chat_auto_coder:main',
            'auto-coder-serve = autocoder.auto_coder_server:main',
            'auto-coder.serve = autocoder.auto_coder_server:main',
            'auto-coder.rag = autocoder.auto_coder_rag:main',
        ],
    },
    package_dir={"": "src"},
    packages=find_packages("src"),    
    package_data={
        "autocoder": ["data/**/*"],
    },
    install_requires=install_requires,    
    classifiers=[                
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    requires_python=">=3.10, <=3.12"
)
