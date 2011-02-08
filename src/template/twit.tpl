<img src='{{ twit.user.profile_image_url }}'/>
<p><a href="http://www.twitter.com/{{ twit.user.screen_name }}"><strong>@{{ twit.user.screen_name }}</strong></a>
{{ twit.text|urlize|escape }}</p>
<p><a href="http://towntwit.appspot.com">TOWNTWIT</a>으로 자동 게시됨</p>