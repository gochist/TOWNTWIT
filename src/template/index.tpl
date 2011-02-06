<html>
<head></head>
<body>
	<a href='{{ logout_url }}'>sign out</a>
	<p>hello, {{ user.user.nickname }}</p>

<hr/>

{% if town_user %}
<p>
<img width=40 height=40 src='{{ town_user.img_url }}'/>
동네 인증 성공 - {{ town_user.name }}({{ town_user.id }})
</p>
{% else %} 
<p> <a href='/town_auth'>동네 인증하기</a> </p>
{% endif %}	

<hr/>

{% if twit_user %}
<p>
<img width=40 height=40 src='{{ twit_user.profile_image_url }}'/>
트위터 인증 성공 - {{ twit_user.name }}({{ twit_user.screen_name }})
</p>
<p>{{ twit_user.status.text }}</p>
{% else %} 
<p> <a href='/twit_auth'>트위터 인증하기</a> </p>
{% endif %}	

<hr/>

<p>
동네-Twit 앱 on GAE/P by 이덕준
</p>
</body>
</html>