# 029-AutoCoder_How to Develop Hybrid Projects

For example, I have a project directory A, which contains:

1. web (a Vue frontend project)
2. server (a Python backend project)

How should I set project_type/source_dir?

You can directly set source_dir to project A. In this case, you may face the following three situations:

## Only modify web

At this time, you can set project_type to `ts`. If `ts` does not meet your needs, you can manually set the file extensions that need to be collected, such as `.vue`, separated by commas if there are multiple. If you need to reference backend code when modifying web code, you can set some backend code paths through urls.

## Only modify server

At this time, you can set project_type to `py` (if it is Java or similar, then set it as `.java`, separated by commas if there are multiple). Similarly, if you need to reference frontend code when modifying server code, you can set some frontend code paths through urls.

## Both web and server need to be modified

At this time, you can set project_type to the file extensions you need to pay attention to, such as `.ts, .vue, .py`.