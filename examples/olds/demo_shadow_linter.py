from autocoder.linters.shadow_linter import ShadowLinter
from autocoder.linters.reactjs_linter import ReactJSLinter
result = {
            'success': False,
            'framework': 'reactjs',
            'files_analyzed': 0,
            'error_count': 0,
            'warning_count': 0,
            'issues': []
        }

project_path = "/Users/allwefantasy/projects/auto-coder.web/frontend"
linter = ReactJSLinter()
# v = linter._convert_raw_lint_result_to_dict(s,result,project_path)
# print(result)

v = linter.lint_file(file_path="/Users/allwefantasy/projects/auto-coder.web/frontend/src/components/MainContent/EditablePreviewPanel.tsx",project_path="/Users/allwefantasy/projects/auto-coder.web")

print(v)

