{% spaceless %}
<table><tr>

<td>
<img src='{{ twit.user.profile_image_url }}'/>
</td>

<td>
<p><a target="_blank" href="http://www.twitter.com/{{ twit.user.screen_name }}">
<strong>{{ twit.user.screen_name }}</strong></a>{{ twit.user.name }}
</p>
<p>{{ twit.text|escape|urlize }}</p>

{% if twit.in_reply_to_status_id %}
<p><a target="_blank" href="http://www.twitter.com/{{ twit.in_reply_to_screen_name }}/status/{{ twit.in_reply_to_status_id }}">in reply to {{ twit.in_reply_to_screen_name }}</a></p>
{% endif %}

</td>

</tr></table>

<hr/>

<p><a href="http://towntwit.appspot.com">TOWNTWIT</a>을 통해 자동 게시함</p>
{% endspaceless %}