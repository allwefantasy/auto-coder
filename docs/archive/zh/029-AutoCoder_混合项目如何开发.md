# 029-AutoCoder_混合项目如何开发

比如我有一个项目目录A，A里面有：

1. web (这是一个vue前端项目)
2. server (这是一个python后端项目)

那我应该如何设置 project_type/source_dir 呢？

你可以直接把 source_dir 可以设置为 A 项目，此时你可能面临下面三种情况：

## 只修改web

这个时候你可以将 project_type 设置为 `ts`。 如果 `ts`无法满足你，你可以手动设置需要收集的文件后缀名，比如 `.vue`之类的，多个可以用逗号隔开。
如果你修改web的代码，需要参考后端的代码，你可以通过 urls 来设置一些后端代码的路径。

## 只修改server

这个时候你可以将 project_type 设置为 `py`(如果是java之类的，那么设置成 `.java`,多个可以用逗号隔开。)。同理如果需要参考前端代码，你可以通过 urls 来设置一些前端代码的路径。

## web和server都要修改

这个时候你可以将 project_type 设置为你需要关注的文件的后缀名，比如 `.ts,.vue,.py`。


