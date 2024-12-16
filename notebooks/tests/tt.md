002-auto-coder.chat初级⼊⻔指南
我们在上⼀篇介绍了如何安装auto-coder.chat Windows:auto-coder.chat安装指南 
MacOS/Linux直接pipinstall-Uauto-coder即可。测试过的python版本为：3.10/3.11
初始化设置
在PowerShell/CMD或者VSCode内置的terminal中输⼊如下指令（auto-coder.chat）：
记得不要忘记了使⽤condaactivateauto-coder切换到合适的环境虚拟环境哟。
第⼀次运⾏，系统会⾃动要求你提供⼀个⼤模型供应商（你后续可以改，⽐如⽤本地的模型或者其他
第三⽅模型），此时会弹出⼀个对话框：
![Image 1](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_1.png)
我们分别给了官⽹，你可以去官⽹注册⼀个账号，你可以⽤上下箭头来切换⽹站，最后⽤Tab键切换
到Ok按钮，然后点击Enter回⻋键确认。
假设我使⽤的是Deepseek官⽹，你应该和我⼀样，在APIKeys⻚⾯创建好了⼀个APIKey：
另外你可以冲⽐如⼀两块钱，这样你就⽤可⽤的Token数余额了：
![Image 2](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_2.png)

![Image 2](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_2.png)
在接下来红框部分输⼊你的APIKey：
![Image 4](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_4.png)
输⼊后点击回⻋，过了⼀会，就会进⼊如下界⾯：
系统监测到当前这个项⽬要不要使⽤auto-coder做初始化，输⼊y,过⼀会，就成功进⼊了主界⾯：
![Image 5](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_5.png)
![Image 5](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_5.png)

第⼀步，我们可以试试/chat指令：
这个时候如果有如下输⼊：
则表明⼀切正常。
核⼼指令介绍
![Image 7](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_7.png)

![Image 7](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_7.png)
![Image 7](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_7.png)
/add_files
我们知道，我们需要对⼀个项⽬进⾏修改或者新增功能，你需要找到需要修改的⽂件以及为了修改这
个⽂件，你可能还需要知道的⼀些其他⽂件。
auto-coder.chat提供了两个可以互相搭配的⽅式。⼀个是⼿动添加关注的⽂件，第⼆个是⾃动根据你
的需求来找到合适的需要修改的⽂件以及参考⽂件。我们先从简单可控的⼊⼿。⼿动添加关注⽂件的
指令就是/add_fiels。
当你使⽤该指令时，系统会⾃动提⽰⽂件：
你可以使⽤Tab来选择对应的⽂件：
添加完成后会告诉你添加了哪个⽂件：
你可以使⽤/list_files指令查看当前所有活跃⽂件：
![Image 10](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_10.png)
![Image 10](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_10.png)
![Image 10](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_10.png)
/add_files还有很多⾼阶能⼒，⽐如使⽤通配符做⽂件添加，类似src\**\*.js这样就可以添加src⽬
录下所有的js⽂件。
也⽀持分组功能，这样可以随时切换⽂件组，灵活的对这些⽂件做操作。
如果你想移除⼀个⽂件，可以使⽤/remove_files
/chat
前⾯我们添加了⽂件以后，就可以使⽤/chat对这些⽂件提问。输⼊：
1
/chat 这个⽂件主要功能是啥
这个时候系统给出如下回复：
![Image 13](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_13.png)
/chat指令⾮常适合闲聊以及针对指定的⼀些⽂件做精确的分析，是看代码的利器之⼀。你也可以问注
⼊python某某个语法具体怎么⽤之类的。
/coding
你肯定迫不及待的想要了解auto-coder.chat的编码功能了。现在来到/coding功能。/coding功能是
要搭配/add_files或者/index/build来使⽤的。
我们这⾥先假设你使⽤的⽅式是/add_files，确保你通过/add_files添加了你想修改的⽂件，以及为
了修改这个⽂件，然后你就可以通过/coding指令描述你的需求了。
1
/coding 我想添加⼀个新的指令 /summon, 该功能调⽤ xxx 完成xxxx
这个时候，auto-coder.chat就会⾃动修改我们通过/add_files添加的活跃⽂件。
这⾥特别注意下：auto-coder.chat是可以创建新⽂件，也可以修改代码，这些都是⾃动完成的，不需
要任何⼿动去复制拷⻉黏贴。
/revert
如果你对auto-coder.chat的修改不满意，可以使⽤/revert指令撤销最近的⼀次提交。如果你⾃⼰⼈
⼯也做了写改动，可以先⽤ git checkout .  先取消掉你的修改，再执⾏/revert指令。
/index/build
![Image 14](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_14.png)
构建索引，可以让auto-coder.chat对你的项⽬有个全局理解，这也是后续/ask指令能够更好⼯作的
重要基础。
也是/coding想实现⾃动找到需要修改的⽂件，⽽⽆需/add_files⼿动添加⽂件的基础。
1
/conf skip_build_index:false
记住关键字是会有提⽰的，不⽤⾃⼰敲：
你可以通过直接输⼊/conf获取你当前做过的配置：
此外，你还需要告诉系统这个项⽬需要索引的⽂件是哪些，可以通过如下指令配置：
1
/conf project_type:py
如果你是python项⽬，配置为py即可。如果你是⼀般的前端项⽬，配置为ts,如果是其他项⽬或者你
想精准的指定哪些⽂件要被索引，可以使⽤后缀名，⽐如我是⼀个scala和java的混合项⽬，我可以
这么设置：
![Image 15](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_15.png)
![Image 15](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_15.png)
1
/conf project_type:.java,.scala
这样就会索引所有.java和.scala后缀的名字了。
现在，让我们开始构建索引：
1
/index/build
根据你项⽬的⼤⼩，可能构建时间⻓短会不⼀致，你可以在⽇志⾥看到进度：
如果你觉得速度太慢，可以通过如下指令设置并发构建的数⽬：
1
/conf index_build_workers:4
注意，通常我们的模型都不会⽀持太⼤的并发，所以⼀般4-8是个⽐较合理的值。
/ask
/ask指令是可以做⼀些项⽬级的提问。这个功能需要开启索引功能。
索引构建好以后，就可以可以问项⽬级别的问题了：
![Image 17](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_17.png)
1
/ask 这个项⽬是⼲嘛的？
这是auto-coder.chat给的回复：
/ask指令是采⽤Agent模式来完成的，如果你觉得效果不好，不妨多问两次。另外，你也可以问⽐如
有多少⾏代码等各种可能的问题。
HumanasModel模式
这个模式你可以通过如下参数开启：
1
/conf human_as_model:true
我们来看⼀个具体例⼦：
1
/coding 修改 help 信息⾥的 /summon 指令的⽂案，⿎励⼤家可以多尝试使⽤。
此时输出信息有两部分值得关注：
![Image 18](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_18.png)

第⼀步部分，前⾯我们通过/add_files指令添加了⼀个chat_auto_coder.py⽂件，然后系统⾃动根据
我们的需求添加了⼀个新的⽂件叫command_temlates.py,这些⽂件都会作为上下⽂最后给到⼤模
型。
第⼆部分，正常这些信息都会直接发给⼤模型，然后直接修改⽂件。因为我们设置了
human_as_model,这个auto-coder.chat不会把这些信息直接发送给⼤模型，⽽是停下来，告诉你，
第⼀，他把所有信息写到了output.txt⽂件⾥了，第⼆个，他把信息黏贴到你的粘贴板⾥了。现在，
auto-coder.chat会等待你的输⼊。
此时，我可以打开deepseek或者Claude官⽹,然后把黏贴到对话框：
![Image 19](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_19.png)
点击回⻋，这个时候web版本的⼤模型就开始解你的需求了：
可以看到，他回复了⼀个可以直接合并的代码块。这⾥我们要复制整个回复，⽽不是复制代码，然后
黏贴回我们的auto-coder.chat的命令⾏，然后点击回⻋，在新⾏输⼊EOF最后再次点击回⻋，这样
就完成代码修改了。
![Image 20](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_20.png)
![Image 20](/Users/allwefantasy/Downloads/kyligence-docs/_images/002-auto-coder.chat-初级入门指南.pdf/image_20.png)
这个模式的好处是，你可以⽤⽹⻚版的⼤模型替代API（API很贵，尤其是当前最好sonnet３.５）。
Claude最近改版，导致不是很好复制，参考 016-更好的⽤human_as_model模式使⽤claude 进
⾏⼀些设置。