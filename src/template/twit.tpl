{% spaceless %}
<table><tr>

<td>
<img src='{{ twit.user.profile_image_url }}'/>
<p><a href="http://www.twitter.com/{{ twit.user.screen_name }}"><strong>{{ twit.user.screen_name }}</strong></a></p>
</td>

<td><p>{{ twit.text|escape|urlize }}</p></td>

</tr></table>

<hr/>

<p><a href="http://towntwit.appspot.com">TOWNTWIT</a>을 통해 자동 게시함</p>
{% endspaceless %}