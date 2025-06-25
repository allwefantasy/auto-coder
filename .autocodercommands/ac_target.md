

{% if path %}
运行脚本如下脚本：
{{ path }}
{% else %}
根据永续需求运行脚本，
{% endif %}
如果脚本有错误，则需要修正相关的代码，直到再次运行没有错误为止，中间不允许停止。

{% if query %}
下面是用户的额外要求：
<query>
{{ query }}
</query>
{% endif %}