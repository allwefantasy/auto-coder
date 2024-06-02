# 037-037-AutoCoder_Project_Quick_Bug_Fix_IN_ACTION

## Bug Description

Today, a seed user reported a bug to me:

![](../images/037-01.png)

It was later discovered that the issue was caused by using absolute paths, which resulted in the files not being filtered out:

![](../images/037-02.png)

I plan to fix this issue and live stream to show a colleague how I can resolve this issue within three minutes.

## Fixing Process (Multiple Images Warning)

I created a new auto-coder yaml file in the project to describe my requirements:

![](../images/037-03.png)

Based on the feedback from the user, I roughly knew that I could perform a validation check when loading the index. So, I described what I wanted auto-coder to do as shown in the image.

Then, I let auto-coder automatically fix the bug:

```bash
auto-coder --file actions/061_index_check_index_file_validity.yml
```

During the execution, a green box popped up asking if these files could meet the subsequent modification requirements. I clicked OK.

Because I prefer using the human_as_model mode, auto-coder provided me with a file, which I pasted into the large model:

![](../images/037-04.png)

I then pasted the entire reply from the large model back to auto-coder (not just the code part, but the complete reply):

![](../images/037-05.png)

At this point, auto-coder will submit the code in diff mode (it also supports wholefile mode, which is more stable but consumes a huge amount of tokens). After auto-coder finishes running, you can open the vscode sidebar to view the commit history:

![](../images/037-06.png)

The entire bug fix involved changing just two lines of code, the added position was very accurate, and the logic was also very precise. After reviewing it, I indicated LGTM.

Next, we validated it (you can also ask it to generate a test code, but unfortunately, I was too rushed when doing it and forgot to mention this), I manually introduced an error:

![](../images/037-07.png)

Then, I ran it again:

![](../images/037-08.png)

You can see the normal error message, and that's a wrap. Of course, you can create a new yaml file and add test cases.

PS: In fact, I tried it twice, once using Opus and once using GPT4 for the code generation part. The former required manual editing (the line breaks were not handled correctly during the merge process), while the latter worked in one go. If you feel it's not good, you can always `auto-coder revert --file actions/061_index_check_index_file_validity.yml` to undo the modification, then make changes, and repeat the process.

## Conclusion

Auto-Coder allows you to make code modifications without having to open a code editor, and the speed is fast enough. It has the potential to be implemented in production, potentially revolutionizing the development process and bringing about intelligent changes. For example, engineers can continuously write project iterations using auto-coder through text, while regular developers perform reviews and test development (also using auto-coder). This may lead to the emergence of new job roles.